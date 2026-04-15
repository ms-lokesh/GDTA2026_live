from django.urls import path

from admin_panel.views import RegistrationBulkStatusView, RegistrationListView, StatsView

urlpatterns = [
    path("registrations", RegistrationListView.as_view()),
    path("registrations/bulk-status", RegistrationBulkStatusView.as_view()),
    path("stats", StatsView.as_view()),
]
