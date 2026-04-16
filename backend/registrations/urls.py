from django.urls import path

from registrations.views import (
    RegistrationAnswerView,
    RegistrationCancelView,
    RegistrationPaymentCreateLinkView,
    RegistrationPaymentStatusView,
    RegistrationStartView,
    RegistrationStatusView,
    RegistrationSubmitView,
)

urlpatterns = [
    path("start", RegistrationStartView.as_view()),
    path("answer", RegistrationAnswerView.as_view()),
    path("status", RegistrationStatusView.as_view()),
    path("cancel", RegistrationCancelView.as_view()),
    path("submit", RegistrationSubmitView.as_view()),
    path("payment/create-link", RegistrationPaymentCreateLinkView.as_view()),
    path("payment/status", RegistrationPaymentStatusView.as_view()),
]
