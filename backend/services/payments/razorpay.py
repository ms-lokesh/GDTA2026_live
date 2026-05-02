import hmac
import hashlib
import requests
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, Optional

from django.conf import settings

from core.exceptions import AppError
from core.constants import ERROR_CODES, COLLECTIONS
from services.firebase.firestore import create_document, query_documents, update_document
from services.payments.receipt import build_receipt_pdf
from utils.payment_logging import log_payment_gateway_error

logger = logging.getLogger(__name__)


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
