from django.urls import path

from operations.views import QRValidateView, VenueDetailView, VenueListCreateView

urlpatterns = [
    path("venues", VenueListCreateView.as_view()),
    path("venues/<str:venue_id>", VenueDetailView.as_view()),
    path("qr/validate", QRValidateView.as_view()),
]
