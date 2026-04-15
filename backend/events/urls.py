from django.urls import path

from events.views import EventDetailView, EventListCreateView

urlpatterns = [
    path("", EventListCreateView.as_view()),
    path("<str:event_id>", EventDetailView.as_view()),
]
