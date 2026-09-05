from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("cv", "0004_cv_imports")]

    operations = [
        migrations.CreateModel(
            name="DocumentArtifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("artifact_type", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX")], max_length=10)),
                ("file", models.FileField(upload_to="cv/artifacts/")),
                ("mime_type", models.CharField(max_length=150)),
                ("template_slug", models.CharField(max_length=100)),
                ("template_config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cv_version", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artifacts", to="cv.cvversion")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="documentartifact",
            index=models.Index(fields=["cv_version", "artifact_type"], name="cv_artifact_type_idx"),
        ),
    ]
