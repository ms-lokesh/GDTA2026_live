from django.conf import settings
from django.db import models

from core.constants import ROLE_VOLUNTEER


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, default=ROLE_VOLUNTEER)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    event_ids = models.JSONField(default=list)
    assigned_venues = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def as_payload(self):
        user = self.user
        role_value = self.role
        return {
            "uid": user.username,
            "id": user.username,
            "username": user.username,
            "name": self.name or user.get_full_name() or user.username,
            "email": user.email,
            "role": role_value,
            "event_ids": self.event_ids or [],
            "assigned_events": self.event_ids or [],
            "assigned_venues": self.assigned_venues or [],
            "is_active": user.is_active and self.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
