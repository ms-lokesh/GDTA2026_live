from django.urls import path

from communications.views import EmailSendView

urlpatterns = [
    path("email/send", EmailSendView.as_view()),
]
