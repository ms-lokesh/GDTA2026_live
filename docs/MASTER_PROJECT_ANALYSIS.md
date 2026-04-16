# GDTA 2026 — Master Project Analysis (Django Only)

Current Backend: **Django + DRF + Firebase**

---

## 1. Architecture state

The repository contains one active backend stack:

- `backend/` (Django + DRF)

No alternate backend runtime exists.

---

## 2. Runtime matrix

| Artifact | Target | Stack |
|---|---|---|
| `Dockerfile` (root) | `backend/` | Django |
| `render.yaml` (root) | `backend/` | Django |
| `backend/Dockerfile` | `backend/` | Django |

---

## 3. Request architecture

```text
HTTP Request
  -> Middleware (logging, auth, role, headers)
  -> API View
  -> Domain Service
  -> Firebase Service Layer
  -> Firestore
  -> Standard Response Envelope
```

Core modules:
- `core/` — constants, exceptions, response contract, audit helper
- `middleware/` — auth, role enforcement, logging, security headers
- `services/firebase/` — Firestore and auth adapter operations
- `services/payments/` — Zoho integration

Domain apps:
- `accounts`
- `events`
- `registrations`
- `operations`
- `admin_panel`
- `communications`

---

## 4. Functional capability snapshot

Implemented:
- Firebase auth middleware
- RBAC and event-level authorization checks
- Events CRUD
- Registration flow with branching + fee matrix
- Zoho payment link/status endpoints
- Venue CRUD + QR validation
- Admin panel stats + bulk status updates
- Export endpoints (registrations/venues/access logs)
- ID-card generation/status APIs
- Email sending and template CRUD
- Volunteer/admin management APIs

Remaining major product-level gap:
- Hackathon module in Django (if required)

---

## 5. API surface

Base path: `/api`

- `/api/health`
- `/api/accounts/*`
- `/api/events/*`
- `/api/registrations/*`
- `/api/operations/*`
- `/api/admin-panel/*`
- `/api/communications/*`

---

## 6. Security posture

- Standardized response envelope
- Sanitized exception handling
- Global security headers
- Request logging + audit logs
- Firestore-only data plane (no Django ORM for domain storage)

---

## 7. Conclusion

The repository is operationally Django-only and production-oriented, with remaining scope focused on optional/domain-specific feature expansion.
