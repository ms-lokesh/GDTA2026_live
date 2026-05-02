from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("collection", models.CharField(db_index=True, max_length=100)),
                ("doc_id", models.CharField(db_index=True, default="", max_length=255)),
                ("data", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "unique_together": {("collection", "doc_id")},
                "indexes": [models.Index(fields=["collection", "doc_id"], name="doc_collection_id_idx")],
            },
        ),
    ]
