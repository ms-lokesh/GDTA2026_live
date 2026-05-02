import uuid

from django.db import models


class Document(models.Model):
    collection = models.CharField(max_length=100, db_index=True)
    doc_id = models.CharField(max_length=255, db_index=True, default="")
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("collection", "doc_id")
        indexes = [
            models.Index(fields=["collection", "doc_id"], name="doc_collection_id_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.doc_id:
            self.doc_id = uuid.uuid4().hex
        super().save(*args, **kwargs)
