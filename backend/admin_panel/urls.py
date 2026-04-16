from django.urls import path

from admin_panel.views import (
    AdminDetailView,
    AdminListCreateView,
    ExportAccessLogsView,
    ExportRegistrationsView,
    ExportVenuesView,
    IdCardGenerateView,
    IdCardStatusView,
    RegistrationBulkStatusView,
    RegistrationListView,
    StatsView,
    VolunteerDetailView,
    VolunteerListCreateView,
)

urlpatterns = [
    path("registrations", RegistrationListView.as_view()),
    path("registrations/bulk-status", RegistrationBulkStatusView.as_view()),
    path("stats", StatsView.as_view()),
    path("export/registrations", ExportRegistrationsView.as_view()),
    path("export/venues", ExportVenuesView.as_view()),
    path("export/access-logs", ExportAccessLogsView.as_view()),
    path("id-card/generate/<str:registration_id>", IdCardGenerateView.as_view()),
    path("id-card/status/<str:registration_id>", IdCardStatusView.as_view()),
    path("volunteers", VolunteerListCreateView.as_view()),
    path("volunteers/<str:user_id>", VolunteerDetailView.as_view()),
    path("admins", AdminListCreateView.as_view()),
    path("admins/<str:user_id>", AdminDetailView.as_view()),
]
