import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cv", "0006_align_career_profile_related_names"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("purpose", models.CharField(choices=[("interview", "Career interview"), ("writer", "CV writer"), ("review", "CV review"), ("job_match", "Job match")], default="interview", max_length=30)),
                ("provider", models.CharField(blank=True, max_length=60)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cv", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ai_conversations", to="cv.cv")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cv_ai_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at", "-id"], "indexes": [models.Index(fields=["owner", "purpose"], name="cv_ai_conv_owner_idx")]},
        ),
        migrations.CreateModel(
            name="AIMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("system", "System"), ("user", "User"), ("assistant", "Assistant")], max_length=20)),
                ("content", models.TextField()),
                ("provider_response_id", models.CharField(blank=True, max_length=150)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="cv.aiconversation")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.CreateModel(
            name="AIExtraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(max_length=60)),
                ("field_name", models.CharField(max_length=120)),
                ("proposed_value", models.JSONField(blank=True, default=dict)),
                ("confirmed", models.BooleanField(db_index=True, default=False)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_cv_ai_extractions", to=settings.AUTH_USER_MODEL)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extractions", to="cv.aiconversation")),
                ("source_message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="extractions", to="cv.aimessage")),
            ],
            options={"ordering": ["-created_at", "-id"], "indexes": [models.Index(fields=["conversation", "confirmed"], name="cv_ai_extract_idx")]},
        ),
        migrations.CreateModel(
            name="ATSAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("provider", models.CharField(blank=True, max_length=60)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ats_analyses", to="cv.aiconversation")),
                ("cv_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ats_analyses", to="cv.cvversion")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cv_ai_ats_analyses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"], "indexes": [models.Index(fields=["owner", "created_at"], name="cv_ai_ats_owner_idx")]},
        ),
    ]
