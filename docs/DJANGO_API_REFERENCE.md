# Django API Reference (`backend/`)

Base path: `/api`

All responses use envelope:

- Success: `{"success": true, "data": ..., "error": null}`
- Error: `{"success": false, "data": null, "error": {"message": "...", "code": "..."}}`

Authentication: Firebase Bearer token (`Authorization: Bearer <token>`) except public paths.

---

## System

### `GET /api/health`
- Auth: public
- Purpose: service heartbeat

---

## Accounts

### `GET /api/accounts/me`
- Auth: required
- Role: any authenticated active user
- Purpose: return authenticated user profile context

---

## Events

### `GET /api/events/`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Returns list of visible events based on role scope

### `POST /api/events/`
- Auth: required
- Role: SUPER_ADMIN only
- Creates an event

### `GET /api/events/{event_id}`
- Auth: required
- Role: ADMIN scoped / SUPER_ADMIN

### `PUT /api/events/{event_id}`
- Auth: required
- Role: ADMIN scoped / SUPER_ADMIN

### `DELETE /api/events/{event_id}`
- Auth: required
- Role: SUPER_ADMIN only

---

## Registrations

### `POST /api/registrations/start`
- Auth: public
- Creates registration session and first question payload

### `POST /api/registrations/answer`
- Auth: public
- Advances state machine with validated answer

### `GET /api/registrations/status?session_id=<id>`
- Auth: public
- Returns session progress snapshot

### `POST /api/registrations/cancel`
- Auth: public
- Cancels active registration session

### `POST /api/registrations/submit`
- Auth: public
- Finalizes registration after state completion

---

## Operations

### `GET /api/operations/venues`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Lists venues for scoped events

### `POST /api/operations/venues`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Creates venue

### `PUT /api/operations/venues/{venue_id}`
- Auth: required
- Role: ADMIN / SUPER_ADMIN

### `DELETE /api/operations/venues/{venue_id}`
- Auth: required
- Role: ADMIN / SUPER_ADMIN

### `POST /api/operations/qr/validate`
- Auth: required
- Role: ADMIN / VOLUNTEER / SUPER_ADMIN
- Validates registration QR against venue rules

---

## Admin Panel

### `GET /api/admin-panel/registrations`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Filters: `status`, `event_id`, `search`, paging controls

### `POST /api/admin-panel/registrations/bulk-status`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Updates status for multiple registrations

### `GET /api/admin-panel/stats`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Returns high-level dashboard stats

---

## Communications

### `POST /api/communications/email/send`
- Auth: required
- Role: ADMIN / SUPER_ADMIN
- Sends SMTP email to recipients and logs results

---

## Common error codes (observed pattern)

- `unauthorized`
- `forbidden`
- `validation_error`
- `not_found`
- `conflict`
- `internal_error`

---

## Notes for integrators

1. Do not parse raw HTTP body shape directly; always read envelope fields.
2. Treat `success=false` as definitive failure even if HTTP code is 200 in transitional paths.
3. Include Firebase token for all non-public endpoints.
4. For admin scopes, include correct event context claims/user role in Firestore user profile.
