from django.urls import path

from chatbot.views import ChatbotMessageView, ChatbotResetView, ChatbotSessionView, ChatbotStartView

urlpatterns = [
    path("start", ChatbotStartView.as_view()),
    path("message", ChatbotMessageView.as_view()),
    path("session", ChatbotSessionView.as_view()),
    path("reset", ChatbotResetView.as_view()),
]
