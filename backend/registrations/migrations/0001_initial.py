import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def rotate_short_registration_ids(apps, schema_editor):
    Document = apps.get_model("datastore", "Document")
    for document in Document.objects.filter(collection="registrations"):
        data = document.data or {}
        unique_id = str(data.get("unique_id") or "")
        if len(unique_id) < 32:
            data["legacy_unique_id"] = unique_id
            data["unique_id"] = str(uuid.uuid4())
            document.data = data
            document.save(update_fields=["data", "updated_at"])


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("datastore", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsentRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("consent_given", models.BooleanField(default=False)),
                ("consent_timestamp", models.DateTimeField(default=django.utils.timezone.now)),
                ("consent_version", models.CharField(max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("consent_text", models.TextField()),
                (
                    "registration",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consent_records", to="datastore.document"),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="consentrecord",
            index=models.Index(fields=["registration", "consent_version"], name="consent_reg_version_idx"),
        ),
        migrations.RunPython(rotate_short_registration_ids, migrations.RunPython.noop),
    ]
