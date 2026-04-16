from django.urls import path

from hackathon.views import (
    HackathonRegistrationDetailView,
    HackathonRegistrationsListView,
    HackathonSendEmailView,
    HackathonStatsView,
)

urlpatterns = [
    path("simple-registrations", HackathonRegistrationsListView.as_view()),
    path("simple-registrations-stats", HackathonStatsView.as_view()),
    path("simple-registrations/send-email", HackathonSendEmailView.as_view()),
    path("simple-registrations/<str:email>", HackathonRegistrationDetailView.as_view()),
]
