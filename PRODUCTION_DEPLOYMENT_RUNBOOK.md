# GDTA 2026 — Production Deployment Runbook (Django Only)

Current Backend: **Django + DRF + Firebase**

---

## 1) Deployment source of truth

- Backend path: `backend/`
- Runtime: `gunicorn project.wsgi:application`
- Deploy artifacts:
  - root `render.yaml`
  - root `Dockerfile`

---

## 2) Required environment variables

### Core
- `DEBUG=False`
- `SECRET_KEY=<strong random key>`
- `ALLOWED_HOSTS=<comma-separated>`
- `CORS_ALLOWED_ORIGINS=<comma-separated https origins>`

### Firebase
- `FIREBASE_CREDENTIALS=<json string>` or
- `FIREBASE_CREDENTIALS_PATH=<path>`

### Email
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_USERNAME`
- `EMAIL_PASSWORD`
- `EMAIL_FROM_NAME`

### Zoho Payments
- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_ORGANIZATION_ID`
- `ZOHO_ACCOUNTS_BASE_URL`
- `ZOHO_BOOKS_API_BASE_URL`
- `ZOHO_REDIRECT_URI`

### Security
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000`

---

## 3) Deployment options

### Option A — Render

Use root `render.yaml` with:

- `rootDir: backend`
- `buildCommand: pip install -r requirements.txt`
- `startCommand: gunicorn project.wsgi:application --bind 0.0.0.0:$PORT ...`

### Option B — Docker (root)

```bash
docker build -t gdta-backend .
docker run --env-file .env -p 8000:8000 gdta-backend
```

---

## 4) Pre-release checklist

- [ ] `/api/health` returns success
- [ ] Firebase auth works on protected routes
- [ ] Role and event-scope checks pass
- [ ] Registration flow works (`/api/registrations/*`)
- [ ] QR validation works with approved registrations
- [ ] Admin panel exports/templates/id-card endpoints verified
- [ ] Security headers present in responses

---

## 5) Smoke tests after deploy

1. `GET /api/health`
2. Auth test on protected endpoint with valid bearer token
3. Registrations start/answer/status/submit
4. Payment create-link/status (staging credentials)
5. Operations QR validate
6. Admin stats/export

---

## 6) Rollback

1. Roll back to previous successful deployment image/revision.
2. Reapply last known-good env vars.
3. Re-check `/api/health` + one protected endpoint.
