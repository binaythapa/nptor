from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cv", "0008_delivery"),
    ]

    operations = [
        migrations.CreateModel(
            name="AISuggestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(max_length=60)),
                ("field_name", models.CharField(max_length=120)),
                ("kind", models.CharField(default="improvement", max_length=40)),
                ("title", models.CharField(max_length=255)),
                ("reason", models.TextField(blank=True)),
                ("current_value", models.JSONField(blank=True, default=dict)),
                ("proposed_value", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected")], db_index=True, default="pending", max_length=20)),
                ("accepted", models.BooleanField(default=False)),
                ("acted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suggestions", to="cv.aiconversation")),
            ],
            options={"ordering": ["created_at", "id"], "indexes": [models.Index(fields=["conversation", "status"], name="cv_ai_sugg_status_idx")]},
        ),
    ]
