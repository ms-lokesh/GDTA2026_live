# GDTA 2026 — Django Backend + Website (Templates + Static)

This repository is a **Django-only** deployment that serves:

- **Public website UI** via Django templates (`backend/templates/*.html`)
- **Static admin/ops tools** via static HTML (`backend/static/*.html`)
- **REST APIs** via Django REST Framework (`/api/*`)

Current stack: **Django + DRF + Firebase**

---

## System status

- Active runtime: `backend/`
- Active deployment: root `Dockerfile` + root `render.yaml`
- Public UI pages are served as templates (no separate frontend server)

---

## UI pages (public) — page-wise features

All pages below are served by Django from `backend/templates/`.

### Landing / Core pages

- `index.html`
	- Hero with video background + image fallback (responsive sizing)
	- Program highlights
	- **Featured Conference Sessions** carousel (uniform card size on each swap)
	- CTA section (registration links are currently gated; see below)

- `about-gdta.html` / `about-gdta-2026.html` / `about-sns.html`
	- About content pages with shared navbar + styling

- `contact.html`
	- Contact / reach-out page

### Program pages

- `program-schedule.html`
	- Schedule / details view

- `program-sessions.html`
	- Sessions & speakers
	- Featured sessions carousel (uniform card size on each swap)

- `program-safari.html`
	- Safari routes page (Route 01/02/03 cards with video)
	- **Route cards are display-only** ("SELECT ROUTE" CTAs removed)
	- Navbar CTA: **Register Now** → `/register-safari.html` (shows coming-soon page)

### Travel & Sponsors

- `travel-stay.html`
	- Travel information and stay guidance

- `sponsors.html`
	- Sponsors/partners page

### Hackathon

- `hackathon.html`
	- Hackathon overview page

### Registration gating (Coming Soon)

Registrations are intentionally not open yet.

- Any of these routes will show the coming-soon screen:
	- `/register.html`
	- `/register-safari.html`
	- `/register-hackathon.html`

- Coming-soon template:
	- `registration-coming-soon.html`
	- Minimal UI: title + **Explore Conference** button
	- Background: `backend/static/img/Background/travel_stay_bg.png`
	- Includes navbar (without a register CTA on the coming-soon screen)

---

## Static tools / dashboards (ops & admin)

These are served from `backend/static/` (not Django templates).

- `admin-dashboard.html` (+ `admin-dashboard.js`)
- `super-admin-dashboard.html` (+ `super-admin-dashboard.js`)
- `super-admin-setup.html`
- `volunteer-login.html`
- `volunteer-dashboard.html`
- `check-in-scanner.html`
- `qr-scanner.html`
- `hackathon-registrations.html` (legacy)

Generated assets:

- `backend/static/templates/id_card_config.json`
- `backend/static/templates/id_card_template.png`

---

## UI behavior notes (recent changes)

- **Chatbot widget removed** from public templates (no embedded chatbot UI).
- `chatbot.html` may exist in templates, but public access is disabled (404).
- Navbar links are styled bold across pages (see `custom-overrides.css`).
- Featured sessions carousel uses fixed sizing + text clamping so cards don’t resize per slide.

Legacy / disabled pages:

- `chatbot.html` exists in `backend/templates/` but is **disabled** (404) by routing.
- `code.html` is a legacy/prototype page (not linked from the main nav).

---

## How routing works for HTML pages

In `backend/project/urls.py`:

- `re_path(r"^(?P<page>[\w\-]+\.html)$", html_page)` serves any `*.html` from `backend/templates/`
- Registration pages are intercepted and redirected to the coming-soon template
- Some public pages can be explicitly disabled (404)

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
- `/api/chatbot/*` (API remains available; UI is disabled)

---

## Repository structure

```text
GDTA2026/
├── backend/                                # Django app (templates + APIs)
│   ├── project/                            # Django settings/urls/asgi/wsgi
│   ├── middleware/                         # auth/logging/security headers
│   ├── services/                           # firebase + payments
│   ├── templates/                          # public website pages (*.html)
│   ├── static/                             # static tools + assets (html/js/css/img)
│   ├── tests/
│   ├── requirements.txt
│   └── manage.py
├── Dockerfile                              # Django runtime container
├── render.yaml                             # Django deployment manifest
├── PRODUCTION_DEPLOYMENT_RUNBOOK.md
└── docs/
```

---

## Local development

From repo root:

1) Create + activate venv, install deps

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Configure env

- Django loads environment variables via `python-dotenv` (`load_dotenv()` in `project/settings.py`).
- The example env file is: `backend/.env.example`
- Create your local env file in the same folder:
	- `backend/.env` (this file is gitignored)
- Minimum for local dev typically includes `DEBUG=True`.

3) Start server

```bash
python manage.py runserver 0.0.0.0:8000
```

Open:

- `http://localhost:8000/index.html`
- Health: `GET http://localhost:8000/api/health`

If port `8000` is busy, run on another port (e.g. `8003`).

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
