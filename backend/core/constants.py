ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_VOLUNTEER = "VOLUNTEER"

ALLOWED_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_VOLUNTEER}

REGISTRATION_STEPS = {
    "CONSENT",
    "NAME",
    "INSTITUTION",
    "ROLE",
    "CATEGORY",
    "ADDONS",
    "COUNTRY",
    "EMAIL",
    "REVIEW",
    "CONFIRM",
    "COMPLETE",
}

COLLECTIONS = {
    "users": "users",
    "events": "events",
    "registrations": "registrations",
    "registration_sessions": "registration_sessions",
    "venues": "venues",
    "access_logs": "access_logs",
    "email_logs": "email_logs",
    "payment_logs": "payment_logs",
    "payment_transactions": "payment_transactions",
    "email_templates": "email_templates",
    "audit_logs": "audit_logs",
    "id_cards": "id_cards",
}

ERROR_CODES = {
    "UNAUTHORIZED": "UNAUTHORIZED",
    "FORBIDDEN": "FORBIDDEN",
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "NOT_FOUND": "NOT_FOUND",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
    "DUPLICATE_EMAIL": "DUPLICATE_EMAIL",
    "INVALID_STATE": "INVALID_STATE",
    "CONFLICT": "CONFLICT",
    "PAYMENT_ERROR": "PAYMENT_ERROR",
    "RATE_LIMITED": "RATE_LIMITED",
}
