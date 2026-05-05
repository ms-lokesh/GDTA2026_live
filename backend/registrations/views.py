from rest_framework.views import APIView
from django.conf import settings
from django.core import signing
from rest_framework.permissions import AllowAny

from core.constants import COLLECTIONS, ERROR_CODES
from core.exceptions import AppError
from core.response import error_response, success_response
from registrations.serializers import (
    AnswerRegistrationSerializer,
    CancelRegistrationSerializer,
    PaytmCallbackSerializer,
    PaymentCreateLinkSerializer,
    PaymentStatusSerializer,
    StartRegistrationSerializer,
    SubmitRegistrationSerializer,
    UnifiedPaymentCreateSerializer,
)
from registrations.state_machine import compute_fee
from registrations.security import PAYMENT_STATUS_TOKEN_MAX_AGE, PAYMENT_STATUS_TOKEN_SALT, is_sanctioned_country
from registrations.services import (
    answer_registration,
    cancel_registration,
    get_session,
    start_registration,
    submit_registration,
)
from services.firebase.firestore import get_document, update_document
from utils.permissions import IsAdminRole
from utils.throttles import ChatbotRateThrottle, PaymentCreateRateThrottle, RegistrationSubmitRateThrottle

# Payment gateways
from services.payments.razorpay import create_payment_order as create_razorpay_payment_order
from services.payments.razorpay import confirm_payment as confirm_razorpay_payment
from services.payments.zoho import create_payment_link, get_payment_status
from services.payments.paytm import (
    PaytmPaymentGateway,
    create_transaction_record as create_paytm_transaction_record,
    find_transaction_by_order_id as find_paytm_transaction_by_order_id,
    generate_order_id,
    mark_transaction_initiated as mark_paytm_transaction_initiated,
    sync_payment_outcome as sync_paytm_payment_outcome,
)


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def _runtime_error_response(exc):
    message = str(exc)
    return error_response(message, ERROR_CODES["VALIDATION_ERROR"], 400)

# --- Paytm Payment Views ---
class PaytmInitiatePaymentView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PaymentCreateRateThrottle]

    def post(self, request):
        # Expecting: order_id, amount, customer_id
        order_id = request.data.get("order_id")
        amount = request.data.get("amount")
        customer_id = request.data.get("customer_id")
        if not order_id or not amount or not customer_id:
            return error_response("Missing order_id, amount, or customer_id", ERROR_CODES["VALIDATION_ERROR"], 400)
        gateway = PaytmPaymentGateway()
        try:
            result = gateway.initiate_payment(order_id=order_id, amount=amount, customer_id=customer_id)
            # Return the transaction token and required info for frontend to redirect
            return success_response(result)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


@method_decorator(csrf_exempt, name="dispatch")
class PaytmCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or request.POST.dict() or {}
        serializer = PaytmCallbackSerializer(data=data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        try:
            order_id = serializer.validated_data["ORDERID"]
            gateway = PaytmPaymentGateway()
            if not gateway.verify_callback_signature(data):
                return error_response("Invalid Paytm callback signature", ERROR_CODES["FORBIDDEN"], 403)

            transaction = find_paytm_transaction_by_order_id(order_id)
            if not transaction:
                return error_response("Transaction not found", ERROR_CODES["NOT_FOUND"], 404)

            paytm_status = gateway.verify_payment(order_id)
            payload = sync_paytm_payment_outcome(
                transaction=transaction,
                paytm_status_payload=paytm_status,
                actor_uid="paytm_callback",
            )

            if payload.get("payment_status") == "paid":
                update_document(
                    COLLECTIONS["registrations"],
                    payload["registration_id"],
                    {
                        "payment_status": "paid",
                        "payment_method": "paytm",
                        "payment_provider": "paytm",
                        "payment_paid_at": payload.get("updated_at"),
                        "payment_updated_at": payload.get("updated_at"),
                        "payment_amount": payload.get("amount"),
                        "paytm_order_id": payload.get("order_id"),
                        "paytm_txn_id": payload.get("txn_id"),
                        "receipt_number": payload.get("receipt_number"),
                        "receipt_download_url": payload.get("receipt_download_url"),
                    },
                )

            return success_response(payload)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data or request.POST.dict() or {}
        try:
            user_obj = getattr(request, "user", None)
            actor_uid = user_obj.get("uid") if isinstance(user_obj, dict) else "public"
            payload = confirm_razorpay_payment(actor_uid=actor_uid, payload=data)
            return success_response(payload)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class RegistrationStartView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StartRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = start_registration(serializer.validated_data.get("session_id"))
            return success_response(data, status=201)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationAnswerView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnswerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            data = answer_registration(
                serializer.validated_data["session_id"],
                serializer.validated_data["answer"],
            )
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return error_response("session_id required", ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            return success_response(get_session(session_id))
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationCancelView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CancelRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            cancel_registration(serializer.validated_data["session_id"])
            return success_response({"cancelled": True})
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationSubmitView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationSubmitRateThrottle]

    def post(self, request):
        serializer = SubmitRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            out = submit_registration(serializer.validated_data, request_meta=request.META)
            status_code = 200 if out.get("reused_registration") else 201
            return success_response(out, status=status_code)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationPaymentCreateLinkView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PaymentCreateRateThrottle]

    def post(self, request):
        serializer = PaymentCreateLinkSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            user_obj = getattr(request, "user", None)
            actor_uid = user_obj.get("uid") if isinstance(user_obj, dict) else "public"
            idempotency_key = request.headers.get("X-Idempotency-Key", "").strip()
            data = create_payment_link(
                actor_uid=actor_uid,
                registration_id=serializer.validated_data["registration_id"],
                name=serializer.validated_data["name"],
                email=serializer.validated_data["email"],
                category=serializer.validated_data["registration_category"],
                addon_food=serializer.validated_data.get("addon_food", False),
                addon_safari=serializer.validated_data.get("addon_safari", False),
                idempotency_key=idempotency_key,
                payment_method="zoho_books",
            )
            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class RegistrationPaymentStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = PaymentStatusSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)
        try:
            user_obj = getattr(request, "user", None)
            actor_uid = user_obj.get("uid") if isinstance(user_obj, dict) else "public"
            payload = get_payment_status(
                actor_uid=actor_uid,
                invoice_id=serializer.validated_data["invoice_id"],
                registration_id=serializer.validated_data.get("registration_id") or "",
                email=serializer.validated_data.get("email") or "",
            )
            return success_response(payload)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class UnifiedPaymentCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PaymentCreateRateThrottle]

    def post(self, request):
        serializer = UnifiedPaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(str(serializer.errors), ERROR_CODES["VALIDATION_ERROR"], 400)

        try:
            user_obj = getattr(request, "user", None)
            actor_uid = user_obj.get("uid") if isinstance(user_obj, dict) else "public"
            payload = serializer.validated_data
            registration_id = payload["registration_id"]
            registration = get_document(COLLECTIONS["registrations"], registration_id)
            if not registration:
                return error_response("Registration not found", ERROR_CODES["NOT_FOUND"], 404)
            if is_sanctioned_country(registration.get("country")):
                return error_response("Registration not available in your region", ERROR_CODES["VALIDATION_ERROR"], 400)

            # Enforce server-side amount validation based on category + selected add-ons.
            fee = compute_fee(
                payload["category"],
                addon_food=payload.get("addon_food", False),
                addon_safari=payload.get("addon_safari", False),
            )
            if not fee:
                return error_response("Invalid category", ERROR_CODES["VALIDATION_ERROR"], 400)

            expected_amount = float(fee.get("total_fee") or 0)
            if str(fee.get("fee_currency") or "").upper() == "USD":
                expected_amount = round(expected_amount * float(getattr(settings, "PAYMENT_USD_TO_INR_RATE", 83.0)), 2)

            payment_method = str(payload["payment_method"]).lower()

            idempotency_key = request.headers.get("X-Idempotency-Key", "").strip()
            if payment_method in {"zoho_books", "zoho"}:
                data = create_payment_link(
                    actor_uid=actor_uid,
                    registration_id=registration_id,
                    name=payload["user_name"],
                    email=payload["email"],
                    category=payload["category"],
                    addon_food=payload.get("addon_food", False),
                    addon_safari=payload.get("addon_safari", False),
                    idempotency_key=idempotency_key,
                    payment_method=payment_method,
                )
            elif payment_method == "razorpay":
                data = create_razorpay_payment_order(
                    actor_uid=actor_uid,
                    registration_id=registration_id,
                    name=payload["user_name"],
                    email=payload["email"],
                    category=payload["category"],
                    addon_food=payload.get("addon_food", False),
                    addon_safari=payload.get("addon_safari", False),
                )
            else:
                return error_response("Unsupported payment method", ERROR_CODES["VALIDATION_ERROR"], 400)

            return success_response(data)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
        except RuntimeError as exc:
            return _runtime_error_response(exc)


class UnifiedPaymentStatusView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, order_id: str):
        user_obj = getattr(request, "user", None)
        actor_uid = user_obj.get("uid") if isinstance(user_obj, dict) else "public"
        token = request.query_params.get("token", "")
        try:
            token_payload = signing.loads(
                token,
                salt=PAYMENT_STATUS_TOKEN_SALT,
                max_age=PAYMENT_STATUS_TOKEN_MAX_AGE,
            )
        except (signing.BadSignature, signing.SignatureExpired):
            return error_response("Forbidden", ERROR_CODES["FORBIDDEN"], 403)

        try:
            payload = get_payment_status(
                actor_uid=actor_uid,
                invoice_id=order_id,
                registration_id=token_payload.get("registration_id") or "",
                email=token_payload.get("email") or "",
            )
            return success_response(payload)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)


class AdminUnifiedPaymentStatusView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request, order_id: str):
        actor_uid = (getattr(request, "user", None) or {}).get("uid", "admin")
        try:
            payload = get_payment_status(actor_uid=actor_uid, invoice_id=order_id)
            return success_response(payload)
        except AppError as exc:
            return error_response(exc.message, exc.code, exc.status_code)
