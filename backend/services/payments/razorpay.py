import hmac
import hashlib
import requests
import logging
import time
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, Optional

from django.conf import settings

from core.audit import write_audit_log
from core.exceptions import AppError
from core.constants import ERROR_CODES, COLLECTIONS
from services.firebase.firestore import create_document, get_document, query_documents, update_document
from services.payments.receipt import build_receipt_pdf
from registrations.state_machine import compute_fee
from utils.payment_logging import log_payment_gateway_error

logger = logging.getLogger(__name__)
_logger = logger
_rate_cache = {"rate": None, "expires_at": 0}
_rate_limit_store = {}


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _normalize_amount(value) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AppError("Invalid payment amount", ERROR_CODES["VALIDATION_ERROR"], 400) from exc

    if amount <= 0:
        raise AppError("Payment amount must be greater than zero", ERROR_CODES["VALIDATION_ERROR"], 400)

    return amount.quantize(Decimal("0.01"))


def find_transaction_by_order_id(order_id: str) -> Optional[Dict]:
    rows = query_documents(COLLECTIONS["payment_transactions"], filters=[("order_id", "==", order_id)], limit=1)
    return rows[0] if rows else None


def generate_receipt_number(order_id: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"GDTA26-{timestamp}-{order_id[-6:]}"


def _rate_limit(key: str, limit: int = 20, window_seconds: int = 60) -> bool:
    now = int(time.time())
    hits = _rate_limit_store.get(key, [])
    start = now - window_seconds
    hits = [h for h in hits if h >= start]
    if len(hits) >= limit:
        _rate_limit_store[key] = hits
        return False
    hits.append(now)
    _rate_limit_store[key] = hits
    return True


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


def _billing_amount_and_currency(fee: Dict) -> tuple[float, str]:
    amount = float(fee.get("total_fee") or 0)
    currency = str(fee.get("fee_currency") or "").upper() or "INR"
    if currency == "USD":
        amount = round(amount * _get_usd_to_inr_rate(), 2)
        currency = "INR"
    return amount, currency


def generate_order_id(registration_id: str) -> str:
    suffix = uuid.uuid4().hex[:8].upper()
    return f"RZP{registration_id.replace('-', '').upper()}-{suffix}"


class RazorpayPaymentGateway:
    def __init__(self):
        self.key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
        self.key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)
        if not self.key_id or not self.key_secret:
            raise AppError("Razorpay is not configured", ERROR_CODES["VALIDATION_ERROR"], 400)
        self.base_url = "https://api.razorpay.com/v1"

    def initiate_payment(self, *, order_id: str, amount, customer_id: str) -> Dict:
        normalized_amount = _normalize_amount(amount)
        # Razorpay expects amount in paise (integer)
        amount_paise = int((normalized_amount * 100).to_integral_value())
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": order_id,
            "payment_capture": 1,
            "notes": {"customer_id": customer_id},
        }
        resp = requests.post(f"{self.base_url}/orders", json=payload, auth=(self.key_id, self.key_secret), timeout=20)
        if resp.status_code >= 400:
            log_payment_gateway_error(logger, "razorpay_order_create", resp, safe_fields=["error"])
            raise AppError("Razorpay order creation failed", ERROR_CODES["PAYMENT_ERROR"], 502)
        data = resp.json() or {}
        # Return data needed by frontend: order id, amount, currency, key id
        return {
            "razorpay_order_id": data.get("id"),
            "amount": f"{normalized_amount:.2f}",
            "currency": data.get("currency", "INR"),
            "key_id": self.key_id,
            "raw": data,
        }

    def verify_callback_signature(self, payload: Dict) -> bool:
        # Expecting payload to contain: razorpay_order_id, razorpay_payment_id, razorpay_signature
        order_id = payload.get("razorpay_order_id") or payload.get("order_id")
        payment_id = payload.get("razorpay_payment_id") or payload.get("payment_id")
        signature = payload.get("razorpay_signature") or payload.get("signature")
        if not order_id or not payment_id or not signature:
            return False
        to_sign = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(self.key_secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_payment(self, order_id: str) -> Dict:
        # Fetch payments for the order and return the API response
        resp = requests.get(f"{self.base_url}/orders/{order_id}/payments", auth=(self.key_id, self.key_secret), timeout=20)
        if resp.status_code >= 400:
            log_payment_gateway_error(logger, "razorpay_payments_fetch", resp, safe_fields=["error"])
            raise AppError("Razorpay payment status check failed", ERROR_CODES["PAYMENT_ERROR"], 502)
        return resp.json() or {}


def create_transaction_record(
    *,
    registration_id: str,
    user_name: str,
    email: str,
    amount,
    order_id: str,
    payment_method: str,
    category: str,
) -> Dict:
    normalized_amount = _normalize_amount(amount)
    existing = find_transaction_by_order_id(order_id)
    if existing:
        raise AppError("Duplicate order detected", ERROR_CODES["CONFLICT"], 409)

    payload = {
        "registration_id": registration_id,
        "user_name": user_name,
        "email": email.lower().strip(),
        "amount": float(normalized_amount),
        "payment_method": payment_method,
        "payment_status": "created",
        "txn_id": None,
        "order_id": order_id,
        "category": category,
        "receipt_number": None,
        "receipt_download_url": None,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    doc_id = create_document(COLLECTIONS["payment_transactions"], payload)
    payload["id"] = doc_id
    return payload


def mark_transaction_initiated(transaction: Dict) -> None:
    update_document(
        COLLECTIONS["payment_transactions"],
        transaction["id"],
        {
            "payment_status": "initiated",
            "updated_at": _utc_now(),
        },
    )


def sync_payment_outcome(*, transaction: Dict, razorpay_status_payload: Dict, actor_uid: str = "public") -> Dict:
    # razorpay_status_payload will contain an "items" list of payments
    items = razorpay_status_payload.get("items") or []
    if not items:
        status = "failed"
    else:
        # pick first payment
        p = items[0]
        status = p.get("status") or "failed"
        txn_id = p.get("id")
        txn_date = p.get("created_at") or _utc_now()

    if status == "captured":
        payment_status = "paid"
    elif status in {"created", "authorized", "attempted"}:
        payment_status = "pending"
    else:
        payment_status = "failed"

    patch = {
        "payment_status": payment_status,
        "txn_id": items[0].get("id") if items else None,
        "gateway_response": razorpay_status_payload,
        "updated_at": _utc_now(),
    }

    if payment_status == "paid":
        receipt_number = transaction.get("receipt_number") or generate_receipt_number(transaction["order_id"])
        receipt_meta = build_receipt_pdf(
            receipt_number=receipt_number,
            registrant_name=transaction.get("user_name") or "",
            email=transaction.get("email") or "",
            category=transaction.get("category") or "",
            amount_paid=float(transaction.get("amount") or 0),
            payment_method="Razorpay",
            transaction_id=patch.get("txn_id") or "",
            payment_date=str(txn_date),
            status="Paid",
        )
        patch.update(receipt_meta)

    update_document(COLLECTIONS["payment_transactions"], transaction["id"], patch)

    # write audit log if available
    try:
        from core.audit import write_audit_log

        write_audit_log(
            "razorpay_payment_status_updated",
            actor_uid,
            target={"order_id": transaction.get("order_id"), "registration_id": transaction.get("registration_id")},
            details={"payment_status": payment_status, "txn_id": patch.get("txn_id")},
        )
    except Exception:
        logger.exception("Failed to write audit log for razorpay status update")

    merged = {**transaction, **patch}
    return {
        "registration_id": merged.get("registration_id"),
        "user_name": merged.get("user_name"),
        "email": merged.get("email"),
        "amount": merged.get("amount"),
        "payment_method": merged.get("payment_method"),
        "payment_status": merged.get("payment_status"),
        "txn_id": merged.get("txn_id"),
        "order_id": merged.get("order_id"),
        "created_at": merged.get("created_at"),
        "updated_at": merged.get("updated_at"),
        "receipt_number": merged.get("receipt_number"),
        "receipt_download_url": merged.get("receipt_download_url"),
    }


def create_payment_order(
    *,
    actor_uid: str,
    registration_id: str,
    name: str,
    email: str,
    category: str,
    addon_food: bool = False,
    addon_safari: bool = False,
) -> Dict:
    if not _rate_limit(f"create:{registration_id}"):
        raise AppError("Too many payment attempts", ERROR_CODES["RATE_LIMITED"], 429)

    fee = compute_fee(category, addon_food=bool(addon_food), addon_safari=bool(addon_safari))
    if not fee:
        raise AppError("Invalid registration category", ERROR_CODES["VALIDATION_ERROR"], 400)

    amount_inr, currency = _billing_amount_and_currency(fee)
    if currency != "INR":
        raise AppError("Razorpay payments must be settled in INR", ERROR_CODES["VALIDATION_ERROR"], 400)

    registration = get_document(COLLECTIONS["registrations"], registration_id)
    if not registration:
        raise AppError("Registration not found", ERROR_CODES["NOT_FOUND"], 404)

    order_id = generate_order_id(registration_id)
    transaction = create_transaction_record(
        registration_id=registration_id,
        user_name=name,
        email=email,
        amount=amount_inr,
        order_id=order_id,
        payment_method="razorpay",
        category=category,
    )

    gateway = RazorpayPaymentGateway()
    gateway_result = gateway.initiate_payment(order_id=order_id, amount=amount_inr, customer_id=registration_id)
    mark_transaction_initiated(transaction)

    update_document(
        COLLECTIONS["registrations"],
        registration["id"],
        {
            "payment_status": "payment_link_created",
            "payment_provider": "razorpay",
            "payment_method": "razorpay",
            "payment_link": None,
            "invoice_id": order_id,
            "razorpay_order_id": order_id,
            "payment_amount": amount_inr,
            "currency": currency,
            "payment_updated_at": _utc_now(),
        },
    )

    write_audit_log(
        "razorpay_payment_order_created",
        actor_uid,
        target={"registration_id": registration_id, "order_id": order_id},
        details={"amount": amount_inr, "currency": currency, "category": category},
    )

    source_currency = str(fee.get("fee_currency") or "INR").upper()
    source_amount = float(fee.get("total_fee") or 0)
    return {
        "provider": "razorpay",
        "order_id": gateway_result.get("razorpay_order_id") or order_id,
        "razorpay_order_id": gateway_result.get("razorpay_order_id") or order_id,
        "key_id": gateway_result.get("key_id"),
        "amount": gateway_result.get("amount") or f"{amount_inr:.2f}",
        "currency": gateway_result.get("currency") or currency,
        "source_amount": source_amount,
        "source_currency": source_currency,
        "name": name,
        "email": email.lower().strip(),
        "description": f"GDTA 2026 registration fee ({category})",
        "prefill": {"name": name, "email": email.lower().strip()},
        "notes": {"registration_id": registration_id, "category": category},
        "raw": gateway_result.get("raw"),
    }


def confirm_payment(*, actor_uid: str, payload: Dict) -> Dict:
    gateway = RazorpayPaymentGateway()
    if not gateway.verify_callback_signature(payload):
        raise AppError("Invalid Razorpay payment signature", ERROR_CODES["FORBIDDEN"], 403)

    order_id = payload.get("razorpay_order_id") or payload.get("order_id")
    if not order_id:
        raise AppError("Razorpay order id is required", ERROR_CODES["VALIDATION_ERROR"], 400)

    transaction = find_transaction_by_order_id(order_id)
    if not transaction:
        raise AppError("Transaction not found", ERROR_CODES["NOT_FOUND"], 404)

    razorpay_status_payload = gateway.verify_payment(order_id)
    outcome = sync_payment_outcome(transaction=transaction, razorpay_status_payload=razorpay_status_payload, actor_uid=actor_uid)

    if outcome.get("payment_status") == "paid":
        update_document(
            COLLECTIONS["registrations"],
            transaction["registration_id"],
            {
                "payment_status": "paid",
                "payment_method": "razorpay",
                "payment_provider": "razorpay",
                "payment_paid_at": outcome.get("updated_at"),
                "payment_updated_at": outcome.get("updated_at"),
                "payment_amount": outcome.get("amount"),
                "currency": "INR",
                "razorpay_order_id": outcome.get("order_id"),
                "razorpay_payment_id": outcome.get("txn_id"),
                "receipt_number": outcome.get("receipt_number"),
                "receipt_download_url": outcome.get("receipt_download_url"),
            },
        )

    return {
        **outcome,
        "provider": "razorpay",
        "verified": True,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payload.get("razorpay_payment_id") or payload.get("payment_id"),
    }
