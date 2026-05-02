import logging
from datetime import datetime, timezone


SENSITIVE_PAYMENT_KEYS = {
    "token",
    "txntoken",
    "card",
    "cvv",
    "account",
    "raw",
    "checksum",
    "checksumhash",
    "signature",
    "vpa",
}


def sanitize_payment_log(value):
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(sensitive in key_text for sensitive in SENSITIVE_PAYMENT_KEYS):
                clean[key] = "[REDACTED]"
            else:
                clean[key] = sanitize_payment_log(item)
        return clean
    if isinstance(value, list):
        return [sanitize_payment_log(item) for item in value[:10]]
    if isinstance(value, str) and len(value) > 250:
        return value[:250] + "...[TRUNCATED]"
    return value


def log_payment_gateway_error(logger, gateway_name, response, safe_fields=None):
    payload = {}
    try:
        payload = response.json() or {}
    except Exception:
        payload = {}

    safe_payload = {}
    if safe_fields:
        safe_payload = {field: payload.get(field) for field in safe_fields if field in payload}

    logger.error(
        "payment_gateway_error timestamp=%s gateway=%s status_code=%s payload=%s",
        datetime.now(timezone.utc).isoformat(),
        gateway_name,
        getattr(response, "status_code", None),
        sanitize_payment_log(safe_payload),
    )
