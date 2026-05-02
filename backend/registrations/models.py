from django.db import models
from django.utils import timezone


class ConsentRecord(models.Model):
    registration = models.ForeignKey(
        "datastore.Document",
        on_delete=models.CASCADE,
        related_name="consent_records",
    )
    consent_given = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(default=timezone.now)
    consent_version = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    consent_text = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=["registration", "consent_version"], name="consent_reg_version_idx"),
        ]
