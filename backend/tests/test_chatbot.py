from unittest.mock import patch
from contextlib import ExitStack

from django.test import SimpleTestCase

from chatbot import services as chatbot_services
from core.exceptions import AppError


class _InMemoryFirestore:
    def __init__(self):
        self.collections = {}

    def create_document(self, collection, data, doc_id=None):
        self.collections.setdefault(collection, {})
        _id = doc_id or f"doc_{len(self.collections[collection]) + 1}"
        self.collections[collection][_id] = dict(data)
        return _id

    def get_document(self, collection, doc_id):
        doc = self.collections.get(collection, {}).get(doc_id)
        if not doc:
            return None
        return {**doc, "id": doc_id}

    def update_document(self, collection, doc_id, data):
        self.collections.setdefault(collection, {})
        current = self.collections[collection].get(doc_id, {})
        current.update(data)
        self.collections[collection][doc_id] = current
        return True

    def query_documents(self, collection, filters=None, limit=None):
        rows = []
        for doc_id, doc in self.collections.get(collection, {}).items():
            ok = True
            for field_name, op, value in filters or []:
                if op != "==":
                    continue
                if doc.get(field_name) != value:
                    ok = False
                    break
            if ok:
                rows.append({**doc, "id": doc_id})
        if limit:
            return rows[:limit]
        return rows


class ChatbotFlowsTests(SimpleTestCase):
    def setUp(self):
        self.mem = _InMemoryFirestore()

    def _patches(self):
        return [
            patch("chatbot.services.create_document", side_effect=self.mem.create_document),
            patch("chatbot.services.get_document", side_effect=self.mem.get_document),
            patch("chatbot.services.update_document", side_effect=self.mem.update_document),
            patch("chatbot.services.query_documents", side_effect=self.mem.query_documents),
        ]

    @patch("chatbot.services.create_payment_link")
    @patch("chatbot.services.submit_registration")
    def test_conference_registration_completes_through_chat(self, mock_submit, mock_payment):
        mock_submit.return_value = {"registration_id": "reg_123", "unique_id": "ABC123XYZ0"}
        mock_payment.return_value = {
            "provider": "zoho_books",
            "invoice_id": "inv_123",
            "payment_link": "https://payments.example/inv_123",
            "currency": "USD",
            "amount": 15,
            "idempotent": False,
        }

        with ExitStack() as stack:
            for p in self._patches():
                stack.enter_context(p)
            started = chatbot_services.start_chat_session("conference_registration")
            session_id = started["session_id"]

            conversation = [
                "yes",
                "John Doe",
                "MIT",
                "Researcher",
                "Foreign Student",
                "no",
                "France",
                "john@example.com",
                "confirm",
            ]

            result = None
            for text in conversation:
                result = chatbot_services.process_chat_message(session_id=session_id, message=text)

            self.assertIsNotNone(result)
            self.assertTrue(result["completed"])
            self.assertEqual(result["registration"]["registration_id"], "reg_123")
            self.assertEqual(result["payment"]["invoice_id"], "inv_123")
            mock_submit.assert_called_once()

    @patch("chatbot.services.create_payment_link")
    @patch("chatbot.services.submit_registration")
    def test_conference_registration_accepts_natural_language(self, mock_submit, mock_payment):
        mock_submit.return_value = {"registration_id": "reg_789", "unique_id": "NATURAL123"}
        mock_payment.return_value = {
            "provider": "zoho_books",
            "invoice_id": "inv_789",
            "payment_link": "https://payments.example/inv_789",
            "currency": "USD",
            "amount": 15,
            "idempotent": False,
        }

        with ExitStack() as stack:
            for p in self._patches():
                stack.enter_context(p)
            started = chatbot_services.start_chat_session("conference_registration")
            session_id = started["session_id"]

            conversation = [
                "yes please proceed",
                "Alex Johnson",
                "Georgia Tech",
                "Product Designer",
                "i am a foreign student",
                "no thanks",
                "i live in france",
                "alex@example.com",
                "yes go ahead and submit it",
            ]

            result = None
            for text in conversation:
                result = chatbot_services.process_chat_message(session_id=session_id, message=text)

            self.assertIsNotNone(result)
            self.assertTrue(result["completed"])
            self.assertEqual(result["registration"]["registration_id"], "reg_789")
            self.assertEqual(result["payment"]["invoice_id"], "inv_789")
            mock_submit.assert_called_once()

    def test_hackathon_track_parses_natural_language(self):
        with ExitStack() as stack:
            for p in self._patches():
                stack.enter_context(p)
            started = chatbot_services.start_chat_session("hackathon_registration")
            session_id = started["session_id"]

            chatbot_services.process_chat_message(session_id=session_id, message="Taylor")
            chatbot_services.process_chat_message(session_id=session_id, message="taylor@example.com")
            chatbot_services.process_chat_message(session_id=session_id, message="+91 9876543210")
            chatbot_services.process_chat_message(session_id=session_id, message="SNS College")
            step = chatbot_services.process_chat_message(
                session_id=session_id,
                message="I prefer smart city problems",
            )

            self.assertFalse(step["completed"])
            self.assertIn("confirm", (step["bot_message"] or "").lower())

    @patch("chatbot.services.gemini_match_choice", return_value=None)
    def test_yes_no_normalizer_handles_natural_phrases_and_boundaries(self, _mock_llm):
        self.assertTrue(chatbot_services._normalize_yes_no("sounds good, let's do it", context="test"))
        self.assertFalse(chatbot_services._normalize_yes_no("no thanks, maybe later", context="test"))

        # Ensure we don't incorrectly match substring 'no' inside unrelated words.
        with self.assertRaises(AppError):
            chatbot_services._normalize_yes_no("innovation", context="test")

    def test_event_planner_generates_two_day_plan(self):
        with ExitStack() as stack:
            for p in self._patches():
                stack.enter_context(p)
            started = chatbot_services.start_chat_session("event_planner")
            session_id = started["session_id"]

            chatbot_services.process_chat_message(session_id=session_id, message="workshops and networking")
            chatbot_services.process_chat_message(session_id=session_id, message="balanced")
            result = chatbot_services.process_chat_message(session_id=session_id, message="plan")

            self.assertTrue(result["completed"])
            self.assertIn("day_1", result["plan"])
            self.assertIn("day_2", result["plan"])
            self.assertGreaterEqual(len(result["plan"]["day_1"]), 3)
            self.assertGreaterEqual(len(result["plan"]["day_2"]), 3)

    @patch("chatbot.services.rag_answer_query")
    def test_conference_assistant_rag_mode_answers_with_sources(self, mock_rag):
        mock_rag.return_value = {
            "answer": "Here’s what I found from conference documents:\n1. Schedule details ...",
            "sources": ["backend/templates/program-schedule.html", "README.md"],
        }

        with ExitStack() as stack:
            for p in self._patches():
                stack.enter_context(p)

            started = chatbot_services.start_chat_session("conference_assistant")
            self.assertEqual(started["mode"], "conference_assistant")
            self.assertIn("Ask me anything", started["bot_message"])

            result = chatbot_services.process_chat_message(
                session_id=started["session_id"],
                message="What is the conference schedule?",
            )

            self.assertFalse(result["completed"])
            self.assertEqual(result["mode"], "conference_assistant")
            self.assertIn("Sources:", result["bot_message"])
            self.assertEqual(len(result.get("rag_sources") or []), 2)
