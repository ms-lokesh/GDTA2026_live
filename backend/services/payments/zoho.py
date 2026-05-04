import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Optional

import requests
from django.conf import settings

from core.audit import write_audit_log
from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from registrations.state_machine import compute_fee
from services.firebase.firestore import create_document, get_document, query_documents, update_document

_token_cache = {"token": None, "expires_at": 0}
_rate_cache = {"rate": None, "expires_at": 0}
_token_lock = threading.Lock()
_rate_limit_store = {}
_rate_limit_lock = threading.Lock()
_logger = logging.getLogger(__name__)


def _zoho_auth_hint(reason: str) -> str:
    key = (reason or "").strip().lower()
    if key == "invalid_code":
        return "Zoho auth failed: refresh token is invalid/expired or is a one-time grant code. Generate a new refresh token and update ZOHO_REFRESH_TOKEN."
    if key == "invalid_client":
        return "Zoho auth failed: client ID/secret mismatch. Verify ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET from the same Zoho app."
    return ""


def _rate_limit(key: str, limit: int = 20, window_seconds: int = 60) -> bool:
    now = int(time.time())
    with _rate_limit_lock:
        hits = _rate_limit_store.get(key, [])
        start = now - window_seconds
        hits = [h for h in hits if h >= start]
        if len(hits) >= limit:
            _rate_limit_store[key] = hits
            return False
        hits.append(now)
        _rate_limit_store[key] = hits
        return True


def _billing_amount_and_currency(fee: Dict) -> tuple[float, str]:
    amount = float(fee.get("total_fee") or 0)
    currency = str(fee.get("fee_currency") or "").upper() or "INR"
    if currency == "USD":
        amount = round(amount * _get_usd_to_inr_rate(), 2)
        currency = "INR"
    return amount, currency


def _get_usd_to_inr_rate() -> float:
    now = int(time.time())
    cached_rate = _rate_cache.get("rate")
    if cached_rate and now < int(_rate_cache.get("expires_at", 0)):
        return float(cached_rate)

    fallback_rate = float(getattr(settings, "PAYMENT_USD_TO_INR_RATE", 83.0))
    url = getattr(settings, "PAYMENT_EXCHANGE_RATE_URL", "").strip()
    if not url:
        return fallback_rate

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        payload = response.json() or {}
        rates = payload.get("rates") or {}
        rate_value = rates.get("INR")
        if rate_value is None:
            _logger.warning("Exchange rate response missing INR; using fallback. body=%s", payload)
            return fallback_rate
        rate = float(rate_value)
    except Exception as exc:
        _logger.warning("Exchange rate fetch failed; using fallback rate. error=%s", exc)
        return fallback_rate

    cache_seconds = int(getattr(settings, "PAYMENT_EXCHANGE_RATE_CACHE_SECONDS", 3600))
    _rate_cache["rate"] = rate
    _rate_cache["expires_at"] = now + max(60, cache_seconds)
    return rate


def _build_invoice_number(registration_id: str) -> str:
    # Zoho Books can require manual invoice numbering; keep it short and unique-ish.
    unique = uuid.uuid4().hex.upper()
    return f"G{unique[:15]}"


def _refresh_access_token(force=False):
    now = int(time.time())
    with _token_lock:
        if (not force) and _token_cache.get("token") and now < int(_token_cache.get("expires_at", 0)) - 30:
            return _token_cache["token"]

        if not settings.ZOHO_CLIENT_ID or not settings.ZOHO_CLIENT_SECRET or not settings.ZOHO_REFRESH_TOKEN:
            raise AppError("Zoho is not configured", ERROR_CODES["VALIDATION_ERROR"], 400)

        response = requests.post(
            f"{settings.ZOHO_ACCOUNTS_BASE_URL}/oauth/v2/token",
            data={
                "refresh_token": settings.ZOHO_REFRESH_TOKEN,
                "client_id": settings.ZOHO_CLIENT_ID,
                "client_secret": settings.ZOHO_CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        if response.status_code >= 400:
            try:
                err = response.json() or {}
                reason = err.get("error") or err.get("message") or err.get("error_description")
            except Exception:
                reason = None
            hint = _zoho_auth_hint(reason)
            if hint:
                raise AppError(hint, ERROR_CODES["PAYMENT_ERROR"], 502)
            detail = f": {reason}" if reason else ""
            raise AppError(f"Unable to refresh Zoho token{detail}", ERROR_CODES["PAYMENT_ERROR"], 502)

        payload = response.json() or {}
        token = (payload.get("access_token") or "").strip()
        if not token:
            reason = payload.get("error") or payload.get("message") or payload.get("error_description")
            hint = _zoho_auth_hint(reason)
            if hint:
                raise AppError(hint, ERROR_CODES["PAYMENT_ERROR"], 502)
            detail = f": {reason}" if reason else ""
            raise AppError(f"Zoho token response invalid{detail}", ERROR_CODES["PAYMENT_ERROR"], 502)

        expires_in = int(payload.get("expires_in", 3600))
        _token_cache["token"] = token
        _token_cache["expires_at"] = now + max(120, expires_in - 60)
        return token


def _zoho_request(method: str, path: str, payload: Optional[Dict] = None, retry=True):
    token = _refresh_access_token()
    url = f"{settings.ZOHO_BOOKS_API_BASE_URL}{path}"
    params = {"organization_id": settings.ZOHO_ORGANIZATION_ID}
    response = requests.request(
        method=method,
        url=url,
        json=payload,
        params=params,
        headers={"Authorization": f"Zoho-oauthtoken {token}"},
        timeout=25,
    )
    if response.status_code == 401 and retry:
        _refresh_access_token(force=True)
        return _zoho_request(method, path, payload, retry=False)
    if response.status_code >= 400:
        _logger.error(
            "Zoho Books API error status=%s url=%s body=%s",
            response.status_code,
            response.url,
            response.text,
        )
        raise AppError("Zoho Books API request failed", ERROR_CODES["PAYMENT_ERROR"], 502)
    return response.json() or {}


def _find_registration(registration_id=None, email=None):
    if registration_id:
        by_id = get_document(COLLECTIONS["registrations"], registration_id)
        if by_id:
            return by_id
    if email:
        rows = query_documents(COLLECTIONS["registrations"], filters=[("email", "==", email.lower().strip())], limit=1)
        if rows:
            return rows[0]
    return None


def _idempotent_existing_link(registration_id: str, idempotency_key: str):
    if not idempotency_key:
        return None
    rows = query_documents(
        COLLECTIONS["payment_logs"],
        filters=[("registration_id", "==", registration_id), ("idempotency_key", "==", idempotency_key)],
        limit=1,
    )
    return rows[0] if rows else None


def create_payment_link(*, actor_uid: str, registration_id: str, name: str, email: str, category: str, addon_food=False, addon_safari=False, idempotency_key="", payment_method=""):
    if not _rate_limit(f"create:{registration_id}"):
        raise AppError("Too many payment attempts", ERROR_CODES["RATE_LIMITED"], 429)

    fee = compute_fee(category, addon_food=bool(addon_food), addon_safari=bool(addon_safari))
    if not fee:
        raise AppError("Invalid registration category", ERROR_CODES["VALIDATION_ERROR"], 400)
    billing_amount, billing_currency = _billing_amount_and_currency(fee)

    selected_method = (payment_method or "zoho_books").strip().lower()
    if selected_method not in {"zoho_books", "zoho"}:
        raise AppError("Only Zoho Books payments are enabled.", ERROR_CODES["VALIDATION_ERROR"], 400)

    existing = _idempotent_existing_link(registration_id, idempotency_key)
    if existing:
        existing_amount = float(existing.get("amount") or 0)
        existing_currency = str(existing.get("currency") or "").upper()
        requested_amount = float(billing_amount)
        requested_currency = str(billing_currency or "").upper()
        if existing_amount == requested_amount and existing_currency == requested_currency:
            return {
                "provider": "zoho_books",
                "invoice_id": existing.get("invoice_id"),
                "payment_link": existing.get("payment_link"),
                "currency": existing.get("currency"),
                "amount": existing.get("amount"),
                "idempotent": True,
            }

    if not settings.ZOHO_ORGANIZATION_ID:
        raise AppError("Zoho organization is not configured", ERROR_CODES["VALIDATION_ERROR"], 400)

    contact_resp = _zoho_request(
        "POST",
        "/contacts",
        payload={
            "contact_name": name,
            "email": email.lower().strip(),
        },
    )

    if str(contact_resp.get("code")) != "0":
        raise AppError("Failed to create Zoho contact", ERROR_CODES["PAYMENT_ERROR"], 502)

    contact_id = ((contact_resp.get("contact") or {}).get("contact_id") or "").strip()
    if not contact_id:
        raise AppError("Zoho contact response missing contact_id", ERROR_CODES["PAYMENT_ERROR"], 502)

    invoice_resp = _zoho_request(
        "POST",
        "/invoices",
        payload={
            "customer_id": contact_id,
            "invoice_number": _build_invoice_number(registration_id),
            "currency_code": billing_currency,
            "reference_number": registration_id,
            "line_items": [
                {
                    "name": f"GDTA 2026 - {category}",
                    "description": f"GDTA 2026 conference registration fee ({category})",
                    "quantity": 1,
                    "rate": billing_amount,
                }
            ],
        },
    )
    if str(invoice_resp.get("code")) != "0":
        raise AppError("Failed to create Zoho invoice", ERROR_CODES["PAYMENT_ERROR"], 502)

    invoice = invoice_resp.get("invoice") or {}
    invoice_id = (invoice.get("invoice_id") or "").strip()
    if not invoice_id:
        raise AppError("Zoho invoice response missing invoice_id", ERROR_CODES["PAYMENT_ERROR"], 502)

    # Move invoice from draft to active/sent so hosted payment page can be opened.
    sent_resp = _zoho_request("POST", f"/invoices/{invoice_id}/status/sent")
    sent_code = str(sent_resp.get("code"))
    if sent_code != "0":
        sent_msg = str(sent_resp.get("message") or "")
        if "already" not in sent_msg.lower():
            raise AppError("Failed to mark Zoho invoice as active", ERROR_CODES["PAYMENT_ERROR"], 502)

    # Re-fetch invoice to get latest customer-facing links after status update.
    invoice_get_resp = _zoho_request("GET", f"/invoices/{invoice_id}")
    if str(invoice_get_resp.get("code")) == "0":
        invoice = invoice_get_resp.get("invoice") or invoice

    payment_link = (
        invoice.get("payment_link")
        or invoice.get("payment_url")
        or invoice.get("invoice_url")
        or invoice.get("customer_view_url")
    )
    if not payment_link:
        raise AppError("No payment URL returned by Zoho", ERROR_CODES["PAYMENT_ERROR"], 502)

    registration = _find_registration(registration_id=registration_id, email=email)
    if not registration:
        raise AppError("Registration not found", ERROR_CODES["NOT_FOUND"], 404)

    update_document(
        COLLECTIONS["registrations"],
        registration["id"],
        {
            "payment_status": "payment_link_created",
            "payment_link": payment_link,
            "invoice_id": invoice_id,
            "payment_amount": billing_amount,
            "currency": billing_currency,
            "payment_provider": "zoho_books",
            "payment_method": payment_method or None,
            "payment_updated_at": datetime.utcnow().isoformat(),
        },
    )

    create_document(
        COLLECTIONS["payment_logs"],
        {
            "registration_id": registration["id"],
            "email": registration.get("email"),
            "invoice_id": invoice_id,
            "payment_link": payment_link,
            "currency": billing_currency,
            "amount": billing_amount,
            "idempotency_key": idempotency_key or None,
            "provider": "zoho_books",
            "action": "create_link",
            "status": "success",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    write_audit_log(
        "payment_link_created",
        actor_uid,
        target={"registration_id": registration["id"], "invoice_id": invoice_id},
        details={"amount": billing_amount, "currency": billing_currency},
    )

    return {
        "provider": "zoho_books",
        "invoice_id": invoice_id,
        "payment_link": payment_link,
        "currency": billing_currency,
        "amount": billing_amount,
        "idempotent": False,
    }


def get_payment_status(*, actor_uid: str, invoice_id: str, registration_id="", email=""):
    if not _rate_limit(f"status:{invoice_id}"):
        raise AppError("Too many payment status checks", ERROR_CODES["RATE_LIMITED"], 429)

    if not settings.ZOHO_ORGANIZATION_ID:
        raise AppError("Zoho organization is not configured", ERROR_CODES["VALIDATION_ERROR"], 400)

    status_resp = _zoho_request("GET", f"/invoices/{invoice_id}")
    if str(status_resp.get("code")) != "0":
        raise AppError("Failed to fetch Zoho invoice status", ERROR_CODES["PAYMENT_ERROR"], 502)

    invoice = status_resp.get("invoice") or {}
    status_value = (invoice.get("status") or "unknown").lower()
    balance = float(invoice.get("balance") or 0)
    paid = status_value == "paid" or balance <= 0

    registration = _find_registration(registration_id=registration_id or invoice.get("reference_number"), email=email or invoice.get("customer_email"))
    if registration:
        update_document(
            COLLECTIONS["registrations"],
            registration["id"],
            {
                "payment_status": "paid" if paid else "payment_pending",
                "invoice_id": invoice_id,
                "payment_provider": "zoho_books",
                "payment_amount": float(invoice.get("total") or registration.get("payment_amount") or 0),
                "currency": invoice.get("currency_code") or registration.get("currency"),
                "payment_paid_at": datetime.utcnow().isoformat() if paid else None,
                "payment_updated_at": datetime.utcnow().isoformat(),
            },
        )

    create_document(
        COLLECTIONS["payment_logs"],
        {
            "registration_id": registration.get("id") if registration else None,
            "email": (registration or {}).get("email") or email,
            "invoice_id": invoice_id,
            "provider": "zoho_books",
            "action": "status_check",
            "status": status_value,
            "paid": paid,
            "balance": balance,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    write_audit_log(
        "payment_status_checked",
        actor_uid,
        target={"registration_id": (registration or {}).get("id"), "invoice_id": invoice_id},
        details={"status": status_value, "paid": paid, "balance": balance},
    )

    return {
        "provider": "zoho_books",
        "invoice_id": invoice_id,
        "status": status_value,
        "balance": balance,
        "paid": paid,
    }
