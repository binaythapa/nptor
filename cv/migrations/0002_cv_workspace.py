from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cv", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CVTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CV",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("completed", "Completed"), ("final", "Final")], default="draft", max_length=20)),
                ("selected_sections", models.JSONField(blank=True, default=dict)),
                ("overrides", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cvs", to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cvs", to="cv.careerprofile")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cvs", to="cv.cvtemplate")),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="cv",
            index=models.Index(fields=["owner", "status"], name="cv_owner_status_idx"),
        ),
        migrations.CreateModel(
            name="CVVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_number", models.PositiveIntegerField()),
                ("snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("cv", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="cv.cv")),
            ],
            options={"ordering": ["-version_number", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="cvversion",
            constraint=models.UniqueConstraint(fields=("cv", "version_number"), name="uniq_cv_version_number"),
        ),
    ]
