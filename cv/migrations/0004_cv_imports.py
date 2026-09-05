from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cv", "0003_align_profile_reverse_names"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CVImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_file", models.FileField(upload_to="cv/imports/")),
                ("original_filename", models.CharField(max_length=255)),
                ("source_type", models.CharField(choices=[("pdf", "PDF"), ("docx", "DOCX")], max_length=10)),
                ("status", models.CharField(choices=[("review", "Review"), ("confirmed", "Confirmed"), ("failed", "Failed")], default="review", max_length=20)),
                ("extracted_text", models.TextField(blank=True)),
                ("parsed_data", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cv_imports", to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="imports", to="cv.careerprofile")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["owner", "status"], name="cv_import_owner_status_idx")],
            },
        ),
        migrations.CreateModel(
            name="ImportedField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(choices=[("contact", "Contact"), ("summary", "Summary"), ("experience", "Experience"), ("education", "Education"), ("skills", "Skills"), ("projects", "Projects"), ("certifications", "Certifications"), ("achievements", "Achievements")], max_length=30)),
                ("field_name", models.CharField(max_length=100)),
                ("value", models.TextField(blank=True)),
                ("confirmed", models.BooleanField(default=False)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("confirmed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_cv_import_fields", to=settings.AUTH_USER_MODEL)),
                ("cv_import", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fields", to="cv.cvimport")),
            ],
            options={
                "ordering": ["section", "field_name", "id"],
                "indexes": [models.Index(fields=["cv_import", "confirmed"], name="cv_imp_field_review_idx")],
            },
        ),
    ]
