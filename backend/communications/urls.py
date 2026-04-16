from django.urls import path

from communications.views import EmailSendView, EmailTemplateDetailView, EmailTemplateListCreateView

urlpatterns = [
    path("email/send", EmailSendView.as_view()),
    path("templates", EmailTemplateListCreateView.as_view()),
    path("templates/<str:template_id>", EmailTemplateDetailView.as_view()),
]
