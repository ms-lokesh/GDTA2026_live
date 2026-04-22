from django.urls import path

from registrations.views import (
    RegistrationAnswerView,
    RegistrationCancelView,
    RegistrationPaymentCreateLinkView,
    RegistrationPaymentStatusView,
    RegistrationStartView,
    RegistrationStatusView,
    RegistrationSubmitView,
    PaytmInitiatePaymentView,
    PaytmCallbackView,
    UnifiedPaymentCreateView,
    UnifiedPaymentStatusView,
)

urlpatterns = [
    path("start", RegistrationStartView.as_view()),
    path("answer", RegistrationAnswerView.as_view()),
    path("status", RegistrationStatusView.as_view()),
    path("cancel", RegistrationCancelView.as_view()),
    path("submit", RegistrationSubmitView.as_view()),
    path("payment/create-link", RegistrationPaymentCreateLinkView.as_view()),
    path("payment/status", RegistrationPaymentStatusView.as_view()),
    path("payment/paytm/initiate", PaytmInitiatePaymentView.as_view()),
    path("payment/paytm/callback", PaytmCallbackView.as_view()),
    path("payment/create", UnifiedPaymentCreateView.as_view()),
    path("payment/status/<str:order_id>", UnifiedPaymentStatusView.as_view()),
]
