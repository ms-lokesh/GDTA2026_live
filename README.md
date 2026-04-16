# GDTA 2026 — Backend Repository (Django Only)

Current Backend: **Django + DRF + Firebase**

---

## System status

This repository is fully Django-only.

- Active runtime: `backend/`
- Active deployment: root `Dockerfile` + root `render.yaml`
- No alternate backend stack remains in this repository

---

## Repository structure

```text
GDTA2026/
├── backend/                                # Active Django backend
│   ├── project/
│   ├── core/
│   ├── middleware/
│   ├── services/
│   │   ├── firebase/
│   │   └── payments/
│   ├── accounts/
│   ├── events/
│   ├── registrations/
│   ├── operations/
│   ├── admin_panel/
│   ├── communications/
│   ├── tests/
│   ├── requirements.txt
│   └── manage.py
├── Dockerfile                              # Django runtime container
├── render.yaml                             # Django deployment manifest
├── PRODUCTION_DEPLOYMENT_RUNBOOK.md
└── docs/
```

---

## Active API surface

Base path: `/api`

- `/api/health`
- `/api/accounts/*`
- `/api/events/*`
- `/api/registrations/*`
- `/api/operations/*`
- `/api/admin-panel/*`
- `/api/communications/*`

---

## Runtime and deployment

### Docker (root)

Root `Dockerfile` runs Django only:

- copies `backend/`
- installs `backend/requirements.txt`
- starts `gunicorn project.wsgi:application`

### Render

Root `render.yaml` points to `backend/` and starts Django via Gunicorn.

---

## Security + architecture notes

- Firebase Auth middleware enforced on protected routes
- Role-based controls: SUPER_ADMIN / ADMIN / VOLUNTEER
- Event-scope checks enforced in service layer
- Standard API envelope across endpoints
- Django ORM is not used for domain data; Firestore is primary store

---

## Local development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py runserver 0.0.0.0:8000
```

Health check: `GET http://localhost:8000/api/health`

---

## Documentation index

- `PRODUCTION_DEPLOYMENT_RUNBOOK.md`
- `docs/MASTER_PROJECT_ANALYSIS.md`
- `docs/DJANGO_API_REFERENCE.md`
- `docs/MIGRATION_GAP_MATRIX.md`
- `SECURITY_VALIDATION_REPORT.md`

---

## Maintainer rule

Any runtime/deployment change must update:

1. `README.md`
2. `PRODUCTION_DEPLOYMENT_RUNBOOK.md`
3. affected deploy artifact (`Dockerfile`, `render.yaml`)
