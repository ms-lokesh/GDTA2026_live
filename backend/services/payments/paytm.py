import json
import importlib
import logging
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional

import requests
from django.conf import settings

from core.audit import write_audit_log
from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from services.firebase.firestore import create_document, query_documents, update_document
from services.payments.receipt import build_receipt_pdf

logger = logging.getLogger(__name__)


def _checksum_client():
    try:
        module = importlib.import_module("paytmchecksum")
        return module.PaytmChecksum
    except ModuleNotFoundError as exc:
        raise AppError(
            "paytmchecksum package is missing. Install dependencies before using Paytm.",
            ERROR_CODES["INTERNAL_ERROR"],
            500,
        ) from exc


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


def generate_order_id(registration_id: str) -> str:
    suffix = uuid.uuid4().hex[:8].upper()
    return f"GDTA{registration_id.replace('-', '').upper()}-{suffix}"


def generate_receipt_number(order_id: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"GDTA26-{timestamp}-{order_id[-6:]}"


class PaytmPaymentGateway:
    def __init__(self):
        self.merchant_id = settings.PAYTM_MERCHANT_ID
        self.merchant_key = settings.PAYTM_MERCHANT_KEY
        self.website = settings.PAYTM_WEBSITE
        self.callback_url = settings.PAYTM_CALLBACK_URL
        self.environment = (getattr(settings, "PAYTM_ENV", "staging") or "staging").strip().lower()

        if not self.merchant_id or not self.merchant_key or not self.callback_url:
            raise AppError("Paytm is not configured", ERROR_CODES["VALIDATION_ERROR"], 400)

        if self.environment == "production":
            base_url = "https://securegw.paytm.in"
        else:
            base_url = "https://securegw-stage.paytm.in"

        self.initiate_url = f"{base_url}/theia/api/v1/initiateTransaction"
        self.status_url = f"{base_url}/v3/order/status"
        self.checkout_url = f"{base_url}/theia/api/v1/showPaymentPage"

    def _generate_signature(self, body: Dict) -> str:
        body_str = json.dumps(body)
        return _checksum_client().generateSignature(body_str, self.merchant_key)

    def verify_callback_signature(self, callback_payload: Dict) -> bool:
        checksum = callback_payload.get("CHECKSUMHASH")
        if not checksum:
            return False

        payload_without_checksum = {k: v for k, v in callback_payload.items() if k != "CHECKSUMHASH"}
        return _checksum_client().verifySignature(payload_without_checksum, self.merchant_key, checksum)

    def initiate_payment(self, *, order_id: str, amount, customer_id: str) -> Dict:
        normalized_amount = _normalize_amount(amount)
        body = {
            "requestType": "Payment",
            "mid": self.merchant_id,
            "websiteName": self.website,
            "orderId": order_id,
            "callbackUrl": self.callback_url,
            "txnAmount": {"value": f"{normalized_amount:.2f}", "currency": "INR"},
            "userInfo": {"custId": customer_id},
        }

        signature = self._generate_signature(body)
        request_payload = {"body": body, "head": {"signature": signature}}

        response = requests.post(
            f"{self.initiate_url}?mid={self.merchant_id}&orderId={order_id}",
            json=request_payload,
            timeout=25,
        )

        if response.status_code >= 400:
            logger.error("Paytm initiate API failed for order %s: %s", order_id, response.text)
            raise AppError("Paytm payment initiation failed", ERROR_CODES["PAYMENT_ERROR"], 502)

        data = response.json() or {}
        body_data = data.get("body") or {}
        txn_token = body_data.get("txnToken")
        result_status = body_data.get("resultInfo", {}).get("resultStatus", "")

        if not txn_token or result_status not in {"S", "PENDING"}:
            raise AppError("Paytm did not return a valid transaction token", ERROR_CODES["PAYMENT_ERROR"], 502)

        return {
            "txnToken": txn_token,
            "order_id": order_id,
            "mid": self.merchant_id,
            "amount": f"{normalized_amount:.2f}",
            "paytm_redirect_url": f"{self.checkout_url}?mid={self.merchant_id}&orderId={order_id}",
            "raw": data,
        }

    def verify_payment(self, order_id: str) -> Dict:
        body = {"mid": self.merchant_id, "orderId": order_id}
        signature = self._generate_signature(body)
        payload = {"body": body, "head": {"signature": signature}}

        response = requests.post(self.status_url, json=payload, timeout=25)
        if response.status_code >= 400:
            logger.error("Paytm status API failed for order %s: %s", order_id, response.text)
            raise AppError("Paytm payment status check failed", ERROR_CODES["PAYMENT_ERROR"], 502)
        return response.json() or {}


def find_transaction_by_order_id(order_id: str) -> Optional[Dict]:
    rows = query_documents(COLLECTIONS["payment_transactions"], filters=[("order_id", "==", order_id)], limit=1)
    return rows[0] if rows else None


def find_open_transaction_for_registration(registration_id: str) -> Optional[Dict]:
    rows = query_documents(
        COLLECTIONS["payment_transactions"],
        filters=[("registration_id", "==", registration_id), ("payment_method", "==", "paytm")],
    )
    open_statuses = {"created", "pending", "initiated", "payment_link_created"}
    for row in rows:
        if str(row.get("payment_status") or "").lower() in open_statuses:
            return row
    return None


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


def sync_payment_outcome(*, transaction: Dict, paytm_status_payload: Dict, actor_uid: str = "public") -> Dict:
    body = paytm_status_payload.get("body") or {}
    result_info = body.get("resultInfo") or {}
    status = (result_info.get("resultStatus") or "").upper()
    txn_id = body.get("txnId") or body.get("TXNID")
    txn_date = body.get("txnDate") or _utc_now()

    if status == "TXN_SUCCESS":
        payment_status = "paid"
    elif status in {"PENDING", "S"}:
        payment_status = "pending"
    else:
        payment_status = "failed"

    patch = {
        "payment_status": payment_status,
        "txn_id": txn_id,
        "gateway_response": body,
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
            payment_method="Paytm",
            transaction_id=txn_id or "",
            payment_date=str(txn_date),
            status="Paid",
        )
        patch.update(receipt_meta)

    update_document(COLLECTIONS["payment_transactions"], transaction["id"], patch)

    write_audit_log(
        "paytm_payment_status_updated",
        actor_uid,
        target={"order_id": transaction.get("order_id"), "registration_id": transaction.get("registration_id")},
        details={"payment_status": payment_status, "txn_id": txn_id},
    )

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
