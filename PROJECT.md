# GDTA 2026 — Consolidated Project Documentation

**Date:** 28 April 2026  
**Current Backend:** Django + DRF + PostgreSQL  
**Status:** Django-only, production-ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Repository Structure](#repository-structure)
4. [API Reference](#api-reference)
5. [Deployment](#deployment)
6. [Environment Variables](#environment-variables)
7. [Security & Validation](#security--validation)
8. [Feature Readiness Matrix](#feature-readiness-matrix)
9. [Local Development](#local-development)
10. [Production Deployment Checklist](#production-deployment-checklist)

---

## Overview

This repository contains the GDTA 2026 backend system, a Django + DRF conference registration platform with integrated chatbot, payment processing, and admin management capabilities.

### System Status

- **Active Runtime:** Django backend (`backend/`)
- **Active Deployment:** Root `Dockerfile` + `render.yaml`
- **Single Stack:** No alternate backend implementations
- **Database:** PostgreSQL (ORM-driven with Django models)
- **Authentication:** API Token-based Bearer tokens

### Key Platforms & Services

- **Registration Flow:** Multi-step branching questionnaire with fee matrix
- **Payments:** Paytm + Zoho Books integration
- **Email:** SMTP-based templating and logging
- **Operations:** Venue management, QR validation, access logging, ID card generation
- **Admin Panel:** Registration filtering, bulk operations, dashboard statistics
- **Communications:** Email templates, notification system

---

## Architecture

### Request Flow

```
HTTP Request
  → Middleware (logging, auth, role, security headers)
  → API View
  → Domain Service
  → Django ORM
  → PostgreSQL Database
  → Standardized Response Envelope
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `core/` | Constants, exceptions, response contract, audit logging |
| `middleware/` | Authentication, role enforcement, logging, security headers |
| `services/firebase/` | External Firebase/Firestore adapters (being deprecated) |
| `services/payments/` | Zoho + Paytm payment gateway integration |

### Domain Applications

| App | Responsibility |
|-----|-----------------|
| `accounts` | User authentication, API token management |
| `events` | Event CRUD and scoping |
| `registrations` | Registration flow, session state machine, payment tracking |
| `operations` | Venues, QR validation, access control, ID cards |
| `admin_panel` | Admin dashboard, bulk operations, exports |
| `communications` | Email templates, sending, notifications |
| `chatbot` | Conversational registration, session storage |
| `hackathon` | Hackathon track registration |

### Data Models (14 Total)

- **User** — Authentication and profile
- **ApiToken** — Bearer token credentials
- **Event** — Conference events with scope boundaries
- **Registration** — Attendee registration records
- **RegistrationSession** — Multi-step form state
- **PaymentTransaction** — Payment records with gateway response
- **PaymentLog** — Payment audit trail
- **Receipt** — Payment receipts and confirmations
- **Venue** — Event venues with access controls
- **AccessLog** — QR check-in records
- **IdCard** — Generated attendee badges
- **EmailTemplate** — Reusable email templates
- **EmailLog** — Sent email audit trail
- **ChatbotSession** — Conversational session persistence
- **HackathonRegistration** — Hackathon track registration
- **AuditLog** — System-wide compliance audit trail

---

## Repository Structure

```
GDTA2026/
├── backend/                               # Active Django backend
│   ├── project/                           # Django project settings
│   │   ├── settings.py                    # Core configuration
│   │   ├── urls.py                        # URL routing
│   │   ├── wsgi.py                        # WSGI entry point
│   │   └── asgi.py                        # ASGI entry point
│   ├── core/                              # Shared utilities
│   │   ├── constants.py                   # App-wide constants
│   │   ├── exceptions.py                  # Custom exceptions
│   │   ├── response.py                    # Response envelope
│   │   ├── audit.py                       # Audit logging
│   ├── middleware/                        # Request/response middleware
│   │   ├── auth_middleware.py             # API token authentication
│   │   ├── logging_middleware.py          # Request logging
│   │   ├── role_middleware.py             # Role-based access
│   │   └── security_headers.py            # Security header injection
│   ├── services/                          # External service adapters
│   │   ├── firebase/                      # Firebase adapters
│   │   └── payments/                      # Payment gateway clients
│   ├── accounts/                          # User & auth module
│   │   ├── models.py                      # User, ApiToken models
│   │   ├── views.py                       # Auth endpoints
│   │   ├── serializers.py                 # Request/response schemas
│   │   ├── urls.py                        # URL routing
│   │   └── admin.py                       # Admin registrations
│   ├── events/                            # Event management
│   ├── registrations/                     # Registration workflow
│   ├── operations/                        # Venue & access control
│   ├── admin_panel/                       # Admin dashboard
│   ├── communications/                    # Email & notifications
│   ├── chatbot/                           # Conversational interface
│   ├── hackathon/                         # Hackathon module
│   ├── tests/                             # Test suite
│   ├── utils/                             # Utility functions
│   ├── static/                            # Bundled frontend files
│   ├── templates/                         # HTML templates
│   ├── manage.py                          # Django CLI tool
│   └── requirements.txt                   # Python dependencies
├── Dockerfile                             # Single Docker build configuration
├── render.yaml                            # Render deployment manifest
├── .dockerignore                          # Docker build exclusions
└── docs/                                  # Additional documentation (consolidated)
```

---

## API Reference

**Base Path:** `/api`

**Response Envelope:**
```json
{
  "success": true,
  "data": { /* payload */ },
  "error": null
}
```

Error responses:
```json
{
  "success": false,
  "data": null,
  "error": {
    "message": "descriptive error",
    "code": "error_code"
  }
}
```

### Authentication

- **Public Endpoints:** Registration flow endpoints (documented below)
- **Protected Endpoints:** Require `Authorization: Bearer <api_token>` header
- **Role Requirements:** SUPER_ADMIN, ADMIN, or VOLUNTEER
- **Bypass Methods:** Admin demo mode on localhost

### System Health

#### `GET /api/health`
- **Auth:** Public
- **Purpose:** Service heartbeat and availability check
- **Response:** `{"success": true, "data": {"status": "ok"}}`

---

### Accounts

#### `GET /api/accounts/me`
- **Auth:** Required
- **Role:** Any authenticated active user
- **Purpose:** Return authenticated user profile context
- **Response:** User object with role, permissions, event scope

---

### Events

#### `GET /api/events/`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Query Params:**
  - `event_id` (optional) — Filter specific event
  - `status` (optional) — "active", "archived"
- **Purpose:** List visible events based on role scope
- **Response:** Array of event objects

#### `POST /api/events/`
- **Auth:** Required
- **Role:** SUPER_ADMIN only
- **Body:** Event creation payload (name, date_range, location, etc.)
- **Purpose:** Create new event
- **Response:** Created event object

#### `GET /api/events/{event_id}`
- **Auth:** Required
- **Role:** ADMIN (scoped), SUPER_ADMIN
- **Purpose:** Get single event details
- **Response:** Event object with computed statistics

#### `PUT /api/events/{event_id}`
- **Auth:** Required
- **Role:** ADMIN (scoped), SUPER_ADMIN
- **Body:** Event update payload
- **Purpose:** Update event configuration
- **Response:** Updated event object

#### `DELETE /api/events/{event_id}`
- **Auth:** Required
- **Role:** SUPER_ADMIN only
- **Purpose:** Soft-delete event (mark as inactive)
- **Response:** Deletion confirmation

---

### Registrations (Public Flow)

#### `POST /api/registrations/start`
- **Auth:** Public
- **Body:** `{ "event_id": "uuid" }`
- **Purpose:** Create registration session and return first question
- **Response:** Session with question payload, session_id

#### `POST /api/registrations/answer`
- **Auth:** Public
- **Body:** `{ "session_id": "uuid", "answer": "value" }`
- **Purpose:** Advance state machine with validated answer
- **Response:** Next question or completion status

#### `GET /api/registrations/status?session_id=<id>`
- **Auth:** Public
- **Query Params:**
  - `session_id` — Active session identifier
- **Purpose:** Poll registration progress without state change
- **Response:** Session progress snapshot (current_step, completed_steps, status)

#### `POST /api/registrations/cancel`
- **Auth:** Public
- **Body:** `{ "session_id": "uuid" }`
- **Purpose:** Cancel active registration session
- **Response:** Cancellation confirmation

#### `POST /api/registrations/submit`
- **Auth:** Public
- **Body:** `{ "session_id": "uuid" }`
- **Purpose:** Finalize registration after state completion
- **Response:** Registration object with ID, payment link (if applicable)

---

### Operations (Admin)

#### `GET /api/operations/venues`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Query Params:**
  - `event_id` (optional)
  - `filter` (optional) — "active", "archived"
- **Purpose:** List venues for scoped events
- **Response:** Array of venue objects with access control status

#### `POST /api/operations/venues`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Body:** Venue creation (name, location, access_limit, etc.)
- **Purpose:** Create new venue
- **Response:** Created venue object

#### `PUT /api/operations/venues/{venue_id}`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Body:** Venue update payload
- **Purpose:** Update venue configuration
- **Response:** Updated venue object

#### `DELETE /api/operations/venues/{venue_id}`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Purpose:** Soft-delete venue
- **Response:** Deletion confirmation

#### `POST /api/operations/qr/validate`
- **Auth:** Required
- **Role:** ADMIN, VOLUNTEER, SUPER_ADMIN
- **Body:** `{ "qr_code": "string", "venue_id": "uuid" }`
- **Purpose:** Validate registration QR against venue rules
- **Response:** Registration details with access granted/denied status

---

### Admin Panel

#### `GET /api/admin-panel/registrations`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Query Params:**
  - `status` (optional) — "pending", "approved", "rejected", "completed"
  - `event_id` (optional)
  - `search` (optional) — Search by name/email
  - `page` (optional) — Pagination (default 1)
  - `limit` (optional) — Page size (default 20)
- **Purpose:** Filter and list registrations with admin visibility
- **Response:** Paginated array of registration objects

#### `POST /api/admin-panel/registrations/bulk-status`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Body:** `{ "registration_ids": ["uuid1", "uuid2"], "new_status": "approved" }`
- **Purpose:** Update status for multiple registrations
- **Response:** Array of updated registration objects with audit log

#### `GET /api/admin-panel/stats`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Query Params:**
  - `event_id` (optional)
  - `date_range` (optional) — "today", "week", "month"
- **Purpose:** Dashboard statistics (totals, by-status breakdown, revenue)
- **Response:** Aggregated statistics object

#### `GET /api/admin-panel/registrations/export`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Query Params:**
  - `format` — "csv" or "json"
  - `status` (optional)
  - `event_id` (optional)
- **Purpose:** Export filtered registrations
- **Response:** File download (CSV/JSON)

---

### Communications (Admin)

#### `POST /api/communications/email/send`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Body:** Email sending request with template/recipients
- **Purpose:** Send SMTP email and log results
- **Response:** Sent email summary with status per recipient

#### `GET /api/communications/templates`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Purpose:** List email templates
- **Response:** Array of template objects

#### `POST /api/communications/templates`
- **Auth:** Required
- **Role:** ADMIN, SUPER_ADMIN
- **Body:** Template creation (name, subject, body, variables)
- **Purpose:** Create reusable email template
- **Response:** Created template object

---

### Error Codes

- `unauthorized` — Missing or invalid API token
- `forbidden` — User lacks required role or event scope
- `validation_error` — Request body validation failed
- `not_found` — Resource not found
- `conflict` — Operation violates business logic (e.g., duplicate email)
- `internal_error` — Server error; see logs

---

## Deployment

### Docker (Recommended)

**Build:**
```bash
docker build -t gdta-backend .
```

**Run:**
```bash
docker run --env-file .env -p 8000:8000 gdta-backend
```

**Dockerfile Highlights:**
- Base image: `python:3.10-slim` (security optimized, smaller footprint)
- User: Non-root `appuser` for security
- Env vars: PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED, DJANGO_SETTINGS_MODULE, DEBUG=False
- Entrypoint: Gunicorn with configurable workers/threads/timeout via environment

### Render Deployment

**Manifest:** `render.yaml`

**Configuration:**
```yaml
services:
  - type: web
    name: gdta-backend-django
    runtime: python
    repo: https://github.com/SRAMBOT08/GDTA2026
    region: oregon
    branch: django (or master/db_1 as appropriate)
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn project.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 4 --timeout 120
```

**Render Environment Zone:** Automatic secret injection from environment variables

### Alternative: Manual WSGI/Gunicorn

```bash
cd backend
pip install -r requirements.txt
gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 3 --threads 4 --timeout 120
```

---

## Environment Variables

### Core Django

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DEBUG` | Yes | `False` | Must be False in production |
| `SECRET_KEY` | Yes | `<50+ random chars>` | Used for session signing |
| `ALLOWED_HOSTS` | Yes | `.onrender.com` | Comma-separated domain list |
| `CORS_ALLOWED_ORIGINS` | Yes | `https://gdta.com` | Comma-separated CORS origins |

### Database (PostgreSQL)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DB_HOST` | Yes | `localhost` or `db.example.com` | PostgreSQL server hostname |
| `DB_PORT` | Yes | `5432` | PostgreSQL port |
| `DB_NAME` | Yes | `gdta_2026` | Database name |
| `DB_USER` | Yes | `gdta_user` | Database user |
| `DB_PASSWORD` | Yes | `<strong password>` | Database password |

### Email (SMTP)

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `EMAIL_HOST` | Yes | `smtp.gmail.com` | SMTP server |
| `EMAIL_PORT` | Yes | `587` | SMTP port (usually 587 for TLS) |
| `EMAIL_USE_TLS` | Yes | `True` | Enable TLS encryption |
| `EMAIL_USERNAME` | Yes | `noreply@gdta.com` | SMTP authentication user |
| `EMAIL_PASSWORD` | Yes | `<app password>` | SMTP authentication password |
| `EMAIL_FROM_NAME` | No | `GDTA 2026 Team` | Display name for sent emails |

### Firebase (Backup/Legacy)

| Variable | Optional | Example | Notes |
|----------|----------|---------|-------|
| `FIREBASE_CREDENTIALS` | Yes | `{...json...}` | Full Firebase service account JSON |
| `FIREBASE_CREDENTIALS_PATH` | Yes | `/secrets/firebase.json` | Path to Firebase credentials file |

**Note:** Firebase support is being phased out in favor of PostgreSQL + API tokens.

### Zoho Payments

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `ZOHO_CLIENT_ID` | Yes | `client_id_from_zoho` | OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Yes | `secret_from_zoho` | OAuth client secret |
| `ZOHO_REFRESH_TOKEN` | Yes | `refresh_token` | Long-lived refresh token |
| `ZOHO_ORGANIZATION_ID` | Yes | `org_id` | Zoho Books organization ID |
| `ZOHO_ACCOUNTS_BASE_URL` | Yes | `https://accounts.zoho.com` | Zoho accounts API base |
| `ZOHO_BOOKS_API_BASE_URL` | Yes | `https://books.zoho.com/api/v3` | Zoho Books API base |
| `ZOHO_REDIRECT_URI` | Yes | `https://app.example.com/callback` | OAuth callback URL |

### Security Headers

| Variable | Recommended | Value | Notes |
|----------|-------------|-------|-------|
| `SESSION_COOKIE_SECURE` | Yes | `True` | HTTPS-only session cookies |
| `CSRF_COOKIE_SECURE` | Yes | `True` | HTTPS-only CSRF cookies |
| `SECURE_HSTS_SECONDS` | Yes | `31536000` | 1-year HSTS header |
| `SECURE_SSL_REDIRECT` | Yes (prod) | `True` | Redirect HTTP→HTTPS |

### Optional/Advanced

| Variable | Default | Example | Notes |
|----------|---------|---------|-------|
| `PYTHON_VERSION` | 3.10 | `3.10.14` | Python runtime version |
| `PORT` | 8000 | `8000` | Gunicorn listen port |
| `GUNICORN_WORKERS` | 3 | `4` | Gunicorn worker count |
| `GUNICORN_THREADS` | 4 | `4` | Threads per worker |
| `GUNICORN_TIMEOUT` | 120 | `120` | Request timeout in seconds |

---

## Security & Validation

### Active Controls

✅ **Authentication & Authorization**
- API token verification middleware (Bearer tokens in Authorization header)
- Role-based route protections (SUPER_ADMIN, ADMIN, VOLUNTEER)
- Event-level scope enforcement for domain operations
- Bypass for demo mode on localhost (admin-panel only)

✅ **Data Protection**
- StandardizedError envelope with sanitized messages (no stack traces to client)
- Input validation via DRF serializers
- SQL injection prevention via Django ORM
- CSRF token validation via middleware

✅ **HTTP Security Headers**
- `X-Frame-Options: DENY` — Clickjacking protection
- `X-Content-Type-Options: nosniff` — MIME-type sniffing prevention
- `Referrer-Policy: strict-origin-when-cross-origin` — Referrer leakage prevention
- `Content-Security-Policy: default-src 'self'` — XSS mitigation
- `Strict-Transport-Security: max-age=31536000` — HTTPS enforcement

✅ **Audit & Compliance**
- Request logging middleware (all endpoints logged)
- Audit logging for privileged mutations (created by action + actor + timestamp)
- Email send logging (EmailLog model tracks delivery status)
- Payment transaction audit trail (PaymentLog + PaymentTransaction models)

### Secret Management

⚠️ **Operational Recommendations:**

1. **Do not commit secrets** to `.env` or anywhere in git
2. **Use root `.env.example`** as template only (no real values)
3. **Store secrets in deployment environment:**
   - Render: Environment variables in dashboard
   - Docker: Pass via `--env-file .env` (not committed)
   - CI/CD: Use secret manager or platform-provided secrets
4. **Rotate credentials periodically:**
   - Firebase service account keys
   - Email provider credentials
   - Zoho OAuth tokens
   - Database password
   - Django SECRET_KEY

### Dependency Security

- **Lock file:** `backend/requirements.txt` contains pinned versions
- **Scanning:** Use `pip-audit` in CI/CD to detect vulnerable packages
- **Monitoring:** Subscribe to security advisories for critical dependencies
- **Updates:** Schedule monthly dependency updates and test thoroughly

### Common Error Codes

- `unauthorized` — Missing/invalid API token
- `forbidden` — Insufficient role or event scope
- `validation_error` — Malformed request body
- `not_found` — Resource doesn't exist
- `conflict` — Business logic violation (e.g., duplicate email)
- `internal_error` — Server error (check logs)

---

## Feature Readiness Matrix

| Capability | Status | Notes |
|-----------|--------|-------|
| PostgreSQL ORM migration | ✅ | 14 models, all services refactored |
| API token authentication | ✅ | Replaces Firebase auth |
| Role-based access control | ✅ | SUPER_ADMIN, ADMIN, VOLUNTEER |
| Events CRUD | ✅ | Full lifecycle management |
| Registration conversational flow | ✅ | Multi-step state machine |
| Fee calculation matrix | ✅ | Category + addon support |
| Duplicate email prevention | ✅ | Enforced in registration flow |
| Payment integration (Paytm) | ✅ | Transaction storage & status tracking |
| Payment integration (Zoho) | ✅ | Link creation, status, receipt generation |
| Admin registration list/filter | ✅ | Full-text search, status filtering |
| Bulk status updates | ✅ | With audit logging |
| Dashboard statistics | ✅ | Payment, status, time-period breakdowns |
| Venue CRUD | ✅ | Access control, capacity limits |
| QR validation & access limits | ✅ | "once", "unlimited", numeric limits |
| Email sending (SMTP) | ✅ | Template system, audit logging |
| Email template CRUD | ✅ | Reusable templates with variables |
| Export (registrations/venues) | ✅ | CSV/JSON formats |
| ID card generation | ✅ | Generate & status tracking |
| Volunteer/admin management | ✅ | CRUD endpoints, role assignment |
| API response envelope | ✅ | Standardized success/error format |
| Security headers | ✅ | CSP, HSTS, X-Frame-Options, etc. |
| Request logging | ✅ | Structured middleware logging |
| Deployment consolidation | ✅ | Single Dockerfile, single Render config |
| Database migrations | ✅ | Django migrate-ready schema |
| Admin panel (Django) | ✅ | All 8 apps registered for operations |
| Chatbot session persistence | ✅ | PostgreSQL-backed ChatbotSession model |
| Hackathon registrations | ✅ | Separate flow with track selection |

---

## Local Development

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- pip + virtualenv

### Setup

```bash
# Clone and navigate
git clone https://github.com/SRAMBOT08/GDTA2026.git
cd GDTA2026/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with local database credentials and secrets

# Run migrations
python manage.py migrate

# Create superuser (optional, for Django admin)
python manage.py createsuperuser

# Run development server
python manage.py runserver 0.0.0.0:8000
```

### Health Check

```bash
curl http://localhost:8000/api/health
# Expected: {"success": true, "data": {"status": "ok"}, "error": null}
```

### Common Commands

```bash
# Run tests
python manage.py test

# Lint (if configured)
flake8 .

# Type checking (if configured)
mypy .

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Django admin
python manage.py createsuperuser
python manage.py changepassword <username>

# Interactive shell
python manage.py shell
```

### Data Migration (Firestore → PostgreSQL)

```bash
# Requires: Firestore credentials file
python scripts/migrate_firestore_to_postgres.py \
  --credentials-path=/path/to/firebase-credentials.json
```

**Features:**
- Idempotent (uses external_id for deduplication)
- Type conversion (Decimal amounts, timezone-aware datetimes)
- FK resolution (User lookups by email/username)
- Comprehensive error handling with rollback support

---

## Production Deployment Checklist

### Pre-Release Tests

- [ ] `/api/health` returns success code
- [ ] Firebase/API token auth works on protected routes
- [ ] Role checks on privileged endpoints (e.g., admin-panel)
- [ ] Event-scope enforcement verified
- [ ] Registration flow: start → answer → submit complete
- [ ] QR validation works with approved venue
- [ ] Admin panel exports (CSV/JSON) functional
- [ ] Email sending and template CRUD work
- [ ] ID card generation operational
- [ ] Payment create-link and status endpoints verified (use staging credentials)

### Smoke Tests After Deploy

1. Test `/api/health` with curl or Postman
2. Test auth: POST a protected endpoint with valid + invalid tokens
3. Run registration flow end-to-end (3-5 min flow)
4. Validate payment integration (staging Zoho/Paytm)
5. Create test admin user and verify admin-panel access
6. Send test email via communications endpoint
7. Confirm security headers in response: `curl -I https://deployed-url/api/health`

### Post-Deployment Verification

- [ ] All environment variables loaded correctly (no missing vars)
- [ ] Database migrations applied successfully
- [ ] No startup errors in application logs
- [ ] Response times acceptable (< 500ms for typical endpoints)
- [ ] All external services reachable (Firebase, Zoho, email SMTP)
- [ ] Error handling graceful (no raw stack traces to client)
- [ ] Security headers present in all responses

### Rollback Procedure

1. Identify previous stable deployment revision/image
2. Revert to previous image or code commit
3. Reapply last known-good environment variables
4. Restart service
5. Verify `/api/health` + one protected endpoint
6. Review logs for any startup errors
7. Run smoke tests again

### Ongoing Monitoring

- Monitor error logs for `internal_error` responses
- Check database connection pool health
- Verify scheduled tasks (email sends, payment reconciliation)
- Track API response times (alert if avg > 1 second)
- Monitor database disk usage
- Verify backups are executing and tested
- Rotate secrets monthly
- Run dependency vulnerability scans weekly
- Test disaster recovery quarterly

---

## Maintainer Guidelines

Any runtime or deployment change must update:

1. **README / PROJECT.md** — Overview and architecture
2. **This file (PROJECT.md)** — All documentation
3. **Affected deploy artifacts:**
   - `Dockerfile` (if runtime/packages change)
   - `render.yaml` (if deployment config changes)
4. **requirements.txt** (if dependencies change)
5. **Test suite** (verify all tests pass after changes)

**Git branching:**
- Main development: `db_1` branch (major features, migrations)
- Hotfixes: `hotfix/*` branch from `main`
- Feature branches: `feature/*` from `db_1`
- All PRs require passing tests before merge

---

## Support & Documentation

- **Django Docs:** https://docs.djangoproject.com/
- **DRF Docs:** https://www.django-rest-framework.org/
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Render Docs:** https://render.com/docs
- **Zoho Books API:** https://www.zoho.com/books/api/v3/
- **Paytm Payments:** https://paytm.com/business/payments/

---

**Last Updated:** 28 April 2026  
**Maintained By:** Development Team  
**Status:** Production Ready
