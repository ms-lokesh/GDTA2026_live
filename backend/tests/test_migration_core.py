from unittest.mock import patch

from django.test import SimpleTestCase
from django.test.client import RequestFactory
from rest_framework.test import APIRequestFactory

from admin_panel.views import RegistrationBulkStatusView
from middleware.firebase_auth import FirebaseAuthMiddleware
from registrations.state_machine import compute_fee, initial_state, process
from registrations.views import RegistrationPaymentCreateLinkView


class RegistrationStateMachineTests(SimpleTestCase):
    def test_registration_branching_to_state_for_india(self):
        state = initial_state()
        answers = [
            "yes",
            "John Doe",
            "IIT",
            "Student",
            "Student",
            "yes",
            "yes",
            "route 01",
            "yes",
            "yes",
            "India",
        ]
        for ans in answers:
            state, _msg, completed = process(state, ans)
            self.assertFalse(completed)

        self.assertEqual(state["current_step"], "STATE")

    def test_registration_branching_skips_state_for_foreign_country(self):
        state = initial_state()
        answers = [
            "yes",
            "Jane Doe",
            "MIT",
            "Researcher",
            "Foreign Student",
            "yes",
            "yes",
            "France",
        ]
        for ans in answers:
            state, _msg, completed = process(state, ans)
            self.assertFalse(completed)

        self.assertEqual(state["current_step"], "EMAIL")

    def test_fee_calculation_matches_expected(self):
        fee = compute_fee("Student", addon_food=True, addon_safari=True)
        self.assertEqual(fee["total_fee"], 1500)
        self.assertEqual(fee["fee_currency"], "INR")


class RBACAndPaymentsTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("admin_panel.views.bulk_update_status")
    def test_bulk_status_forbidden_for_volunteer(self, mock_bulk):
        class DummyRequest:
            data = {"registration_ids": ["r1"], "status": "approved"}
            user = {"uid": "v1", "role": "VOLUNTEER", "event_ids": ["e1"]}

        response = RegistrationBulkStatusView().post(DummyRequest())
        self.assertEqual(response.status_code, 403)
        mock_bulk.assert_not_called()

    @patch("registrations.views.create_payment_link")
    def test_payment_create_link_uses_idempotency_header(self, mock_create_payment_link):
        mock_create_payment_link.return_value = {
            "provider": "zoho_books",
            "invoice_id": "inv_1",
            "payment_link": "https://payments.example/inv_1",
            "currency": "INR",
            "amount": 1500,
            "idempotent": False,
        }
        request = self.factory.post(
            "/api/registrations/payment/create-link",
            {
                "registration_id": "reg_1",
                "name": "John Doe",
                "email": "john@example.com",
                "registration_category": "Student",
                "addon_food": True,
                "addon_safari": True,
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="idem-123",
        )
        request.user = None

        response = RegistrationPaymentCreateLinkView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        args, kwargs = mock_create_payment_link.call_args
        self.assertEqual(kwargs["idempotency_key"], "idem-123")


class FirebaseAuthMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_public_path_bypasses_bearer_auth(self):
        middleware = FirebaseAuthMiddleware(lambda _req: type("Resp", (), {"status_code": 200})())
        request = self.request_factory.get("/api/health")
        response = middleware(request)
        self.assertEqual(getattr(response, "status_code", 500), 200)

    def test_missing_bearer_token_returns_401(self):
        middleware = FirebaseAuthMiddleware(lambda _req: type("Resp", (), {"status_code": 200})())
        request = self.request_factory.get("/api/admin-panel/registrations")
        response = middleware(request)
        self.assertEqual(getattr(response, "status_code", 500), 401)
