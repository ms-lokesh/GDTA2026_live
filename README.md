# GDTA 2026 SaaS Blueprint (Stack-Agnostic Rebuild Guide)

This document is a **detailed product + engineering specification** for rebuilding the GDTA conference SaaS in a different tech stack.

If you are porting this system to Node/Nest, Java/Spring, .NET, Go, Rails, or serverless, this README is designed to be your migration map.

---

## 1) Product scope

The platform combines 6 capabilities in one SaaS:

1. **Public conference site** (content pages, schedule/travel/sponsors, etc.)
2. **Chat assistant** for conference FAQs + schedule help + registration flow
3. **Registration system** with fee logic and optional payment links
4. **Admin back-office** (review, approval, exports, email, templates)
5. **Operations module** (venues, volunteers, QR validation, access logs)
6. **Hackathon module** (full submissions + simplified ticket queue)

Core app lives in `admin_system/` with entrypoint `admin_system/app.py`.

---

## 2) Architecture (current implementation)

### 2.1 Runtime and layers

- **Web/API layer**: Flask blueprints (`routes/*`)
- **Business logic layer**: deterministic modules (`logic/*`)
- **Data layer**: Firestore models (`db/firebase_models.py`)
- **Conversation memory**: SQLite (`db/conversation_store.py`)
- **LLM layer**: intent + RAG (`llm/*`)
- **UI layer**: static admin pages + template-rendered public pages

### 2.2 Design principle

The backend keeps the control plane:

- deterministic logic for planning/registration/access decisions
- LLM only assists with language interpretation and natural responses

This principle should be preserved in the rebuild.

---

## 3) Repository map

```text
GDTA2026/
├── Dockerfile
├── PRODUCTION_DEPLOYMENT_RUNBOOK.md
├── SECURITY_VALIDATION_REPORT.md
└── admin_system/
    ├── app.py
    ├── routes/
    ├── logic/
    ├── db/
    ├── llm/
    ├── static/
    ├── templates/
    ├── data/
    ├── tests/
    └── migration/setup scripts
```

---

## 4) Bounded contexts you should keep in the new stack

Treat these as separate modules/services even if deployed as a monolith first:

1. **Identity & Access**
   - admin/super-admin/volunteer auth
   - session and role checks

2. **Conference Content**
   - conference metadata
   - session catalog

3. **Registration**
   - attendee registration workflow
   - fee/add-on logic
   - payment status tracking

4. **Planning**
   - schedule creation
   - clash avoidance

5. **Operations**
   - venues
   - volunteers
   - QR validation
   - access logs

6. **Communications**
   - SMTP sends
   - email templates
   - email logs

7. **Hackathon**
   - full registration pipeline
   - simple ticket-style queue

8. **AI Assistant**
   - intent classification
   - RAG answer generation

---

## 5) Domain model (canonical entities)

Use this section as your schema contract for a rebuild.

### 5.1 `Event`

- `id` (internal doc id)
- `event_id` (external slug; e.g., `gdta-2026`)
- `name`, `year`, `start_date`, `end_date`
- `location`, `description`
- `is_active`
- `created_at`, `updated_at`, `created_by`

### 5.2 `AdminUser`

- `username` (primary id)
- `password_hash`
- `email`, `name`
- `role` (`admin` or `super_admin`)
- `assigned_events: string[]`
- `is_active`, `created_at`, `last_login`

### 5.3 `Registration` (conference attendee)

- identity/profile:
  - `title`, `name`, `gender`, `email`, `institution`, `role`
- registration metadata:
  - `event_id`
  - `registration_source` (`chatbot` / `form`)
  - `session_id` (chat linkage)
  - `status` (`pending` / `approved` / `rejected`)
- compliance:
  - `consent`, `gdta_member`, `gdta_affiliation`
- geography:
  - `country`, `state`
- pricing:
  - `registration_category`
  - `addon_food_accommodation`, `addon_safari`, `safari_route`
  - `fee_currency`, `base_fee`, `addon_food_accommodation_fee`, `addon_safari_fee`, `total_fee`, `fixed_all_inclusive`
- payment:
  - `payment_status`, `payment_provider`, `payment_invoice_id`, `payment_link`, `payment_amount`, `payment_currency`, `payment_method`, `payment_paid_at`
- ID/entry:
  - `unique_id` (QR identity)
  - `id_card_generated`, `id_card_generated_at`, `id_card_url`, `id_card_regenerate_approved`
  - `checked_in`, `checked_in_at`, `checked_in_by`
- audit:
  - `admin_notes`, `created_at`, `updated_at`

### 5.4 `Venue`

- `id`, `event_id`, `name`
- `venue_type` (`entry`, `food`, `session`, `lounge`, `other`)
- `description`, `location`, `capacity`
- `is_active`, `requires_approval`
- `access_limit` (`unlimited`, `once`, or numeric string)
- `created_at`, `created_by`

### 5.5 `Volunteer`

- `username` (primary id)
- `password_hash`
- `name`, `email`, `phone`
- `event_id`
- `assigned_venues: string[]`
- `is_active`, `created_at`, `created_by`, `last_login`

### 5.6 `AccessLog`

- `registration_id`, `registration_email`, `participant_name`
- `event_id`, `venue_id`, `venue_name`
- `action_type` (`check-in`, `check-out`, `denied`)
- `scanned_by`, `timestamp`
- `notes`, `qr_code`

### 5.7 `EmailTemplate`

- `name`, `category`, `is_active`, `event_id`
- `subject`, `body`
- `variables: string[]`
- `created_by`, `created_at`, `updated_at`

### 5.8 `EmailLog`

- `registration_id`, `recipient_email`
- `subject`, `body`
- `sent_by`, `sent_at`
- `status`, `error_message`

### 5.9 `HackathonRegistration` (full)

- user profile + institution + role + location
- participation metadata (track/type/team)
- technical profile (skills, links, experience)
- submission info (`submission_url`, `submission_date`)
- moderation (`status`, `score`, `judge_notes`, `admin_notes`)
- `unique_id`, `created_at`, `updated_at`

### 5.10 `SimpleHackathonRegistration` (ticket queue model)

- `name`, `email`, `phone`, `college`, `track`
- queue metadata:
  - `ticket_id`, `status`, `priority`, `assigned_to`
  - `last_contact_at`, `resolved_at`
  - `admin_notes`, `ticket_history[]`
- `created_at`, `updated_at`

---

## 6) Registration state machine (critical to preserve)

Defined in `logic/registration.py`.

### 6.1 States

`CONSENT -> NAME -> INSTITUTION -> ROLE -> REGISTRATION_CATEGORY -> ADDON_FOOD_ACCOMMODATION -> ADDON_SAFARI -> (optional SAFARI_ROUTE) -> GDTA_MEMBER -> GDTA_AFFILIATION -> COUNTRY -> (optional STATE) -> EMAIL -> REVIEW -> CONFIRMATION -> COMPLETED`

### 6.2 Conditional transitions

- If `consent = No` => terminate flow.
- If category is fixed all-inclusive => skip add-on questions.
- If `addon_safari = No` => skip safari route and clear route.
- If `country != India` => skip `STATE`.
- In `REVIEW`, user can edit specific fields then return to review.

### 6.3 Validation highlights

- email regex validation
- category/option normalization
- required-field validation before submit
- duplicate email rejection before final save

---

## 7) Fee and pricing rules (source: backend logic)

The authoritative pricing is in `logic/registration.py::FEE_CONFIG`.

### 7.1 Categories

- Student: INR base 500 + optional food 500 + optional safari 500
- Academician: INR base 2000 + optional food 500 + optional safari 500
- Industry People: INR 7500 fixed all-inclusive
- Foreign Student: USD 15 fixed
- Foreign Academician: USD 100 fixed
- Foreign Industry People: USD 100 fixed
- Foreign Delegate: USD 100 fixed

### 7.2 Important parity note

Some chatbot/fallback textual responses mention a different public fee narrative in certain flows. For rebuild correctness, treat **deterministic backend fee config** as source of truth for transaction logic.

---

## 8) Scheduling/planning logic

Defined in `logic/planner.py` + `logic/clash_detector.py`.

### 8.1 Planning algorithm (deterministic)

1. Filter sessions by interest/tags
2. Group by day + time slots
3. Select 1 session per slot (priority to matching interest)
4. Validate clashes
5. Return summary + metadata

### 8.2 API support

- plan generation
- alternatives in same slot
- custom plan clash validation

---

## 9) QR access control logic

Defined in `logic/access_control.py`.

### 9.1 Validation sequence

1. Find attendee by `unique_id` (fallback to email for backward compatibility)
2. Ensure registration status is `approved`
3. Ensure venue exists and `is_active`
4. Enforce `access_limit` (`once`, numeric, or unlimited)
5. Write access log with success/denial reason

### 9.2 Rebuild recommendation

For stricter security in new stack, consider removing email fallback and enforcing QR token signatures.

---

## 10) API inventory (complete route map)

This is the current practical contract surface.

### 10.1 System & UI routes

- `GET /api`
- `GET /chatbot`
- `GET /admin`
- `GET /admin/hackathon-registrations`
- `GET /register`
- `GET /`
- `GET /index`
- `GET /hackathon`
- `GET /hackathon1.html` (legacy redirect)
- `GET /<page>.html`
- `GET /static/<path:filename>`
- `GET /static/generated_ids/<filename>`

### 10.2 Chat routes

- `POST /api/chat`
- `POST /api/state`

### 10.3 Planning routes

- `GET /api/sessions`
- `POST /api/plan`
- `GET /api/alternatives/<session_id>`
- `POST /api/validate`

### 10.4 Registration routes

- `POST /api/register/start`
- `POST /api/register/answer`
- `POST /api/register/cancel`
- `GET /api/register/status`
- `POST /api/register/submit-form`

### 10.5 Payment (Zoho Books)

- `POST /api/register/payment/zoho-books/create-link`
- `GET /api/register/payment/zoho-books/status`

### 10.6 Conversation data lifecycle

- `POST /api/conversation/end`
- `POST /api/conversation/cleanup`

### 10.7 Admin auth/profile

- `POST /api/admin/login`
- `POST /api/admin/logout`
- `GET /api/admin/me`

### 10.8 Registration administration

- `GET /api/admin/registrations`
- `GET /api/admin/registrations/<registration_id>`
- `PUT /api/admin/registrations/<registration_id>`
- `DELETE /api/admin/registrations/<registration_id>`
- `POST /api/admin/registrations/bulk/approve`
- `POST /api/admin/registrations/bulk/reject`
- `POST /api/admin/registrations/bulk/status`
- `POST /api/admin/registrations/bulk/email`

### 10.9 Check-in and access ops

- `POST /api/admin/check-in`
- `GET /api/admin/check-in/stats`
- `GET /api/admin/access-logs`
- `GET /api/admin/access-logs/venue/<venue_id>`
- `GET /api/admin/access-logs/participant/<registration_email>`
- `GET /api/admin/venues/<venue_id>/stats`
- `POST /api/validate-qr`
- `POST /api/validate-qr/check-duplicate`

### 10.10 Email templates

- `GET /api/admin/email-templates`
- `GET /api/admin/email-templates/<template_id>`
- `POST /api/admin/email-templates`
- `PUT /api/admin/email-templates/<template_id>`
- `DELETE /api/admin/email-templates/<template_id>`
- `POST /api/admin/email-templates/<template_id>/preview`

### 10.11 Email sending

- `POST /api/admin/email/send`

### 10.12 Exports

- `GET /api/admin/export/registrations`
- `GET /api/admin/export/venues`
- `GET /api/admin/export/volunteers`
- `GET /api/admin/export/id-cards-bulk`
- `GET /api/admin/export/badge-list`
- `GET /api/admin/export/qr-codes`

### 10.13 ID-card management

- `POST /api/admin/id-card/generate/<registration_id>`
- `GET /api/admin/id-card/view/<unique_id>`
- `POST /api/admin/id-card/batch`
- `POST /api/admin/id-card/approve-regenerate/<registration_id>`
- `GET /api/admin/id-card/status/<registration_id>`

### 10.14 Venue management

- `GET /api/admin/venues`
- `GET /api/admin/venues/<venue_id>`
- `POST /api/admin/venues`
- `PUT /api/admin/venues/<venue_id>`
- `DELETE /api/admin/venues/<venue_id>`

### 10.15 Volunteer management

- `POST /api/volunteer/login`
- `POST /api/volunteer/logout`
- `GET /api/volunteer/me`
- `GET /api/admin/volunteers`
- `GET /api/admin/volunteers/<username>`
- `POST /api/admin/volunteers`
- `PUT /api/admin/volunteers/<username>`
- `DELETE /api/admin/volunteers/<username>`

### 10.16 Event/admin management

- `GET /api/admin/events`
- `GET /api/admin/admins`
- `POST /api/admin/admins`
- `PUT /api/admin/admins/<username>`
- `DELETE /api/admin/admins/<username>`
- `GET /api/superadmin/events`
- `POST /api/superadmin/events`
- `PUT /api/superadmin/events/<event_id>`
- `DELETE /api/superadmin/events/<event_id>`
- `GET /api/superadmin/admins`
- `POST /api/superadmin/admins`
- `PUT /api/superadmin/admins/<username>`
- `DELETE /api/superadmin/admins/<username>`
- `POST /api/super-admin-setup`

### 10.17 Hackathon

- `POST /api/hackathon/register`
- `GET /api/hackathon/registrations`
- `GET /api/hackathon/registration/<registration_id>`
- `PUT /api/hackathon/registration/<registration_id>`
- `POST /api/hackathon/registration/<registration_id>/submit`
- `DELETE /api/hackathon/registration/<registration_id>`
- `GET /api/hackathon/stats`
- `POST /api/hackathon/simple-register`
- `GET /api/hackathon/simple-registrations`
- `GET /api/hackathon/simple-registrations/<email>`
- `PUT /api/hackathon/simple-registrations/<email>`
- `POST /api/hackathon/simple-registrations/send-email`
- `DELETE /api/hackathon/simple-registrations/<email>`
- `GET /api/hackathon/simple-registrations-stats`

---

## 11) Authentication and authorization model

### 11.1 Current mechanism

- Cookie-based server sessions for admin/volunteer flows
- role checks via decorators:
  - `require_auth`
  - `require_super_admin`
  - `require_admin_or_volunteer_auth`

### 11.2 Firebase Auth integration

Admin login supports Firebase email/password validation when configured.

- `FIREBASE_WEB_API_KEY`
- `FIREBASE_AUTH_REQUIRED`

If strict mode is on and Firebase auth fails, login is denied.

### 11.3 Rebuild recommendation

Move to short-lived JWT/opaque tokens with refresh strategy, keeping role+event scopes in claims.

---

## 12) Security controls currently implemented

From `app.py` and tests:

- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- Content Security Policy header
- optional HSTS when request is HTTPS
- state-changing `/api/admin*` and `/api/superadmin*` origin/referer gate
- hardened session cookies (`HttpOnly`, `SameSite=Lax`, configurable `Secure`)

Security baseline test file:

- `admin_system/tests/test_security_baseline.py`

---

## 13) Environment variables (actual keys used in code)

### Core app/security

- `SECRET_KEY`
- `PORT`
- `FLASK_ENV`
- `FLASK_DEBUG`
- `CORS_ORIGINS`
- `SESSION_COOKIE_SECURE`
- `ENABLE_SECURITY_HEADERS`
- `REQUIRE_ORIGIN_FOR_STATE_CHANGING`
- `RENDER` (deployment behavior note)

### Firebase

- `FIREBASE_CREDENTIALS` (JSON string) OR local credentials file
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_AUTH_REQUIRED`

### Email (SMTP)

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`
- `EMAIL_FROM_NAME`

### LLM

- `LLM_ENABLED`
- `LLM_CONFIDENCE_THRESHOLD`
- `LLM_TIMEOUT`
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `GROK_API_KEY`

### Zoho Books payment

- `ZOHO_BOOKS_DATA_CENTER`
- `ZOHO_BOOKS_CLIENT_ID`
- `ZOHO_BOOKS_CLIENT_SECRET`
- `ZOHO_BOOKS_REFRESH_TOKEN`
- `ZOHO_BOOKS_ACCESS_TOKEN` (fallback)
- `ZOHO_BOOKS_ORGANIZATION_ID`
- `ZOHO_BOOKS_PAYMENT_LINK_TEMPLATE`

---

## 14) Integrations and side effects

### 14.1 Firebase Firestore

- Primary source for events, users, registrations, templates, logs

### 14.2 SMTP

- sends bulk/individual/admin-triggered emails
- logs send status/errors

### 14.3 Zoho Books

- creates contact + invoice + payment URL
- status polling updates registration payment fields

### 14.4 ID-card generation

- image generation with QR and attendee metadata
- files stored in `static/generated_ids/`

---

## 15) Build and run (current stack)

### Local

```bash
cd admin_system
pip install -r requirements.txt
python app.py
```

Local URLs:

- `http://localhost:5000/`
- `http://localhost:5000/chatbot`
- `http://localhost:5000/register`
- `http://localhost:5000/admin`

### Docker

```bash
docker build -t gdta-admin:prod .
docker run --name gdta-admin -p 5000:5000 --env-file .env.prod gdta-admin:prod
```

---

## 16) Operational scripts

Main scripts in `admin_system/`:

- `migrate_to_multi_event.py`
- `migrate_existing_registrations.py`
- `migrate_add_event_id.py`
- `create_default_event.py`
- `create_super_admin.py`
- `setup_render.py`
- `rotate_admin_account.py`

Debug/verification scripts:

- `debug_chat_outputs.py`
- `debug_intents.py`
- `debug_rag_call.py`
- `test_chatbot_strict.py`

---

## 17) Rebuild in a different stack: implementation strategy

If you are recreating this SaaS, use this sequence.

### Phase 1 — Domain-first foundation

1. Model entities from Section 5 in your target DB
2. Implement repository/data access layer
3. Add migration + seed for default event/admin

### Phase 2 — Core deterministic engines

1. Port registration state machine exactly
2. Port fee computation and validations
3. Port scheduler + clash detector
4. Port QR access policy engine

### Phase 3 — API and auth

1. Implement route groups by bounded context
2. Add role-based authorization middleware
3. Add session/JWT strategy and CSRF/origin safeguards

### Phase 4 — Integrations

1. SMTP + templating
2. payment provider integration with webhook/polling strategy
3. ID card generation pipeline

### Phase 5 — AI assistant

1. Intent classification interface (provider-agnostic)
2. RAG answer service with deterministic fallback
3. Chat context storage with TTL cleanup

### Phase 6 — Back-office UX + exports

1. Admin dashboard APIs + filters
2. CSV/Excel/PDF export services
3. Volunteer scanner UI and ops flows

---

## 18) Suggested target architecture patterns (stack-agnostic)

### 18.1 Service boundaries (single deploy, modular code)

- `auth-service`
- `registration-service`
- `planning-service`
- `ops-service` (venues/volunteers/qr)
- `communication-service` (email/template)
- `hackathon-service`
- `ai-assistant-service`

### 18.2 Data stores

- relational DB for transactional integrity (recommended)
- object storage for generated cards/exports
- redis/cache for sessions and rate limiting

### 18.3 Eventing (recommended enhancement)

Emit events like:

- `registration.submitted`
- `registration.approved`
- `id_card.generated`
- `payment.link_created`
- `payment.confirmed`
- `qr.access_granted|denied`

---

## 19) Quality attributes and non-functional requirements

### Availability

- health checks for app + dependencies
- graceful degradation for LLM provider downtime

### Security

- strict CORS allowlist
- authenticated admin surfaces only
- encrypted secrets management
- audit logs for privileged actions

### Observability

- structured logs with request IDs
- metrics (latency, error rate, queue depth)
- traces across integrations

### Performance

- pagination on list endpoints
- async/batch jobs for heavy exports and email bursts
- cache static conference/session metadata

---

## 20) Risks and parity caveats for migration

1. **Legacy compatibility behaviors** exist (e.g., QR email fallback).
2. **Mixed persistence** in current code (Firestore + SQLite conversation store).
3. **Potential duplication/conflict** in route declarations should be normalized during rebuild.
4. **Textual chatbot fee copy** may diverge from deterministic fee config.
5. **Filesystem outputs** (ID cards) need object storage strategy in cloud-native architecture.

---

## 21) Parity checklist for the new stack

Use this to decide when migration is “feature complete.”

- [ ] Multi-event admin model with role-scoped access
- [ ] Registration state machine parity (all conditional branches)
- [ ] Fee calculation parity and validation parity
- [ ] Scheduling + clash parity
- [ ] QR policy and access log parity
- [ ] Email templates + send logs parity
- [ ] Export parity (CSV/Excel/PDF)
- [ ] Hackathon full + simple pipeline parity
- [ ] Payment link/status parity
- [ ] Security header/origin gate parity
- [ ] Chat intent + RAG fallback parity

---

## 22) Related docs in this repo

- `PRODUCTION_DEPLOYMENT_RUNBOOK.md`
- `SECURITY_VALIDATION_REPORT.md`
- `admin_system/README.md`
- `admin_system/RENDER_DEPLOYMENT.md`
- `admin_system/VERIFY_DEPLOYMENT.md`

---

## 23) Maintainer note

When changing behavior/contracts, update this file first.

This README is intended to be the **canonical migration and architecture spec** for future re-platforming.
