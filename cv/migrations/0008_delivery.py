import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cv", "0007_ai_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("email", "Email"), ("whatsapp", "WhatsApp"), ("viber", "Viber")], max_length=20)),
                ("document_format", models.CharField(max_length=10)),
                ("recipient", models.CharField(max_length=320)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")], default="pending", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("provider", models.CharField(blank=True, max_length=60)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("artifact", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="cv.documentartifact")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cv_delivery_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"], "indexes": [models.Index(fields=["owner", "channel", "status"], name="cv_delivery_owner_idx")]},
        ),
    ]
