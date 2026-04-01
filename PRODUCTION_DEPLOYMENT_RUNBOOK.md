# GDTA 2026 — Production Deployment Runbook

This guide is the **single source of truth** for moving the project from development to production with Docker, including Firebase/Auth migration, security checks, secrets, and release steps.

---

## 1) What changed for production readiness

At repository root (`c:\Python310\GDTA2026`):

- `Dockerfile` (root-level, production-oriented)
  - Runs `admin_system` via Gunicorn
  - Uses non-root runtime user
  - Supports `PORT` and Gunicorn tuning env vars
- `.dockerignore`
  - Excludes secrets (`.env`, Firebase credential files), venv, caches, and local debug/test artifacts

---

## 2) Deployment architecture (recommended)

- **Web app/API**: Dockerized Flask app (`admin_system/app.py` via `app:app`)
- **Database/Auth**: Firebase (Firestore + Firebase Authentication)
- **Email**: SMTP provider (Gmail or enterprise SMTP)
- **LLM**: Gemini/OpenAI/Grok keys via env vars
- **Payments**: Keep payment provider credentials only in secrets manager/env

---

## 3) Environment variables (production)

Use your platform secret manager (Render, Cloud Run, ECS, Kubernetes, etc.).

### Core runtime

- `FLASK_ENV=production`
- `FLASK_DEBUG=False`
- `SECRET_KEY=<long-random-value>`
- `PORT=5000` (or platform-provided)
- `CORS_ORIGINS=https://your-main-domain.com,https://admin.your-main-domain.com`

### Firebase (backend)

- `FIREBASE_CREDENTIALS=<full service-account JSON as string>`
  - Recommended for containers; avoids bundling credential files into images.

### Firebase Auth (admin/volunteer login path)

- `FIREBASE_WEB_API_KEY=<firebase-web-api-key>`
- `FIREBASE_AUTH_REQUIRED=True` (set `True` only when all admin/volunteer users are ready with emails/password flow)

### Email

Code uses these keys:
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_PORT=587`
- `EMAIL_USE_TLS=True`
- `EMAIL_USERNAME=<smtp-user>`
- `EMAIL_PASSWORD=<smtp-password-or-app-password>`
- `EMAIL_FROM_NAME=GDTA 2026 Team`

### LLM / AI

- `LLM_ENABLED=True`
- `LLM_CONFIDENCE_THRESHOLD=0.6`
- `LLM_TIMEOUT=5`
- One or more API keys:
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY`
  - `OPENAI_API_KEY` (optional)
  - `GROK_API_KEY` (optional)

### Payment integration (if enabled in backend)

- `ZOHO_BOOKS_DATA_CENTER`
- `ZOHO_BOOKS_CLIENT_ID`
- `ZOHO_BOOKS_CLIENT_SECRET`
- `ZOHO_BOOKS_REFRESH_TOKEN`
- `ZOHO_BOOKS_ACCESS_TOKEN` (fallback only)
- `ZOHO_BOOKS_ORGANIZATION_ID`
- `ZOHO_BOOKS_PAYMENT_LINK_TEMPLATE`

> Note: Keep these in secrets manager only; never in git.

---

## 4) Firebase migration plan (DEV → PROD)

## 4.1 Create/prepare production Firebase project

1. Create a new Firebase project for production.
2. Enable Firestore.
3. Enable Firebase Authentication (Email/Password if used).
4. Create a service account with minimum required permissions.
5. Store service-account JSON into `FIREBASE_CREDENTIALS` secret.

## 4.2 Data migration

Choose one method:

- **Method A (recommended):** Firestore export/import via Google Cloud tools.
- **Method B:** Controlled script migration if schema transformation is required.

Validate after migration:
- Event documents present
- Registrations count matches source
- Admin/volunteer records present
- Random sample spot-check for critical fields (`event_id`, status, unique IDs)

## 4.3 Auth migration / cutover

Before setting `FIREBASE_AUTH_REQUIRED=True`:

1. Ensure every admin/volunteer account has valid email.
2. Provision Firebase Auth users (matching UID strategy used by backend).
3. Verify login with 2–3 pilot accounts.
4. Enable `FIREBASE_AUTH_REQUIRED=True` only after successful pilot.

Rollback switch:
- Temporarily set `FIREBASE_AUTH_REQUIRED=False` to restore legacy login path while fixing auth mapping.

---

## 5) Docker build and run (root-level)

Run from repository root (`c:\Python310\GDTA2026`).

### Build image

- `docker build -t gdta-admin:prod .`

### Run container

- `docker run --name gdta-admin -p 5000:5000 --env-file .env.prod gdta-admin:prod`

Where `.env.prod` contains only production-safe keys and no comments with secrets shared publicly.

### Smoke test

- Open `http://localhost:5000/api`
- Open `http://localhost:5000/admin`
- Open `http://localhost:5000/register`

---

## 6) Security hardening checklist (must pass before go-live)

## App/config

- [ ] `FLASK_ENV=production`
- [ ] `FLASK_DEBUG=False`
- [ ] Strong `SECRET_KEY` configured
- [ ] `CORS_ORIGINS` restricted to exact production domains
- [ ] No wildcard CORS in production

## Secrets

- [ ] No secrets committed in repo history
- [ ] `.env`, Firebase JSON, API keys excluded from image/context (`.dockerignore`)
- [ ] Secrets are injected at runtime (secret manager/env vars)
- [ ] Secret rotation plan documented (Firebase, SMTP, LLM, payment)

## Firebase/Auth

- [ ] Production Firebase project separate from development
- [ ] Principle of least privilege for service account
- [ ] Auth cutover tested with pilot users
- [ ] Rollback path confirmed (`FIREBASE_AUTH_REQUIRED=False`)

## Infra/runtime

- [ ] Container runs as non-root user
- [ ] HTTPS termination enabled at load balancer/platform
- [ ] Access logs and error logs captured/retained
- [ ] Alerting configured for 5xx spike and crash loops

## Functional checks

- [ ] Admin login works
- [ ] Registration submit + status updates work
- [ ] Email sending works
- [ ] Payment link/status path works (if enabled)
- [ ] Chatbot still responds under `LLM_ENABLED` setting

---

## 7) Release procedure

## 7.1 Pre-release

1. Freeze code on release commit/tag.
2. Backup/Export DEV and PROD Firestore snapshots.
3. Confirm all prod secrets are populated.
4. Build and deploy to staging (if available) or pre-prod instance.

## 7.2 Go-live

1. Deploy new container image.
2. Run smoke tests (`/api`, `/admin`, `/register`, core APIs).
3. Monitor logs and error rates for 30–60 minutes.
4. Announce completion.

## 7.3 Post-release

- Validate registration throughput and admin workflows.
- Check email and payment success rates.
- Confirm no auth lockouts.

---

## 8) Rollback plan

If critical issue detected:

1. Roll back to previous known-good image tag.
2. Set `FIREBASE_AUTH_REQUIRED=False` if auth cutover caused failures.
3. Revert changed secrets only if they are the root cause.
4. Re-run smoke tests.

---

## 9) Recommended next improvements (optional but valuable)

- Add `/healthz` endpoint and container `HEALTHCHECK`
- Add CI pipeline to run lint/tests + image vulnerability scan
- Add WAF/rate-limits at edge in addition to app-level limits
- Add structured JSON logging + centralized log dashboard

---

## 10) Ownership matrix

- **App deploy owner:** Backend/DevOps
- **Firebase owner:** Platform/Backend
- **Auth cutover owner:** Backend + Admin Ops
- **Secrets owner:** Platform/Security
- **Go-live approver:** Project lead

---

## 11) Security validation artifacts (completed)

This repository now includes concrete security validation deliverables:

- `SECURITY_VALIDATION_REPORT.md` (summary of implemented controls + scan outputs)
- `admin_system/tests/test_security_baseline.py` (automated baseline checks)

Run security baseline tests:

- `c:/Python310/GDTA2026/.venv/Scripts/python.exe -m unittest admin_system/tests/test_security_baseline.py`

Run dependency audit:

- `cd admin_system`
- `c:/Python310/GDTA2026/.venv/Scripts/python.exe -m pip_audit --local`

Post-upgrade recommendation:

- Rebuild your runtime/container after dependency upgrades in `admin_system/requirements.txt`.
- Re-run both baseline tests and dependency audit before production cutover.

---

Last updated: 2026-04-01
