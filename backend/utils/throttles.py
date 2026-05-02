from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class RegistrationSubmitRateThrottle(AnonRateThrottle):
    scope = "registration_submit"


class PaymentCreateRateThrottle(AnonRateThrottle):
    scope = "payment_create"


class ChatbotRateThrottle(AnonRateThrottle):
    scope = "chatbot"


class AdminUserRateThrottle(UserRateThrottle):
    scope = "admin_user"
