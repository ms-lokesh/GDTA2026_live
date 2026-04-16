# Django Readiness Matrix (Post-Cleanup)

Current Backend: **Django + DRF + Firebase**

Legend:
- ✅ Implemented
- 🟨 Partial/optional follow-up
- ❌ Not implemented

| Capability Area | Status | Notes |
|---|---|---|
| Firebase auth verification | ✅ | Middleware-based token verification |
| Role-based access control | ✅ | Role middleware + decorators + event scoping |
| Events CRUD | ✅ | Implemented |
| Registration conversational flow | ✅ | Branching and validation in Django |
| Fee calculation matrix | ✅ | Category + addon matrix implemented |
| Registration duplicate checks | ✅ | Email duplicate guard |
| Payment integration (Zoho) | ✅ | Create link + status |
| Admin registration list/filter | ✅ | Implemented |
| Bulk status updates | ✅ | Implemented with audit log |
| Dashboard stats | ✅ | Includes payment dimensions |
| Venue CRUD | ✅ | Implemented |
| QR validation + access limits | ✅ | Implemented with access logging |
| Email sending | ✅ | SMTP + logs |
| Email template CRUD | ✅ | Implemented |
| Export endpoints | ✅ | Registrations, venues, access logs |
| ID card generation | ✅ | Generate + status |
| Volunteer/admin management APIs | ✅ | CRUD endpoints |
| Standardized API envelope | ✅ | Unified success/error format |
| Security headers middleware | ✅ | Enabled globally |
| Structured request logging | ✅ | Middleware logging enabled |
| Deployment consistency | ✅ | Root Docker + Render aligned to Django |
| Hackathon module | ❌ | Pending product decision and implementation |

---

## Current acceptance status

1. Single active backend stack in repository
2. Single runtime/deploy path (Django)
3. Core conference/admin flows operational in Django
4. Remaining gaps are feature scope decisions, not migration ambiguity
