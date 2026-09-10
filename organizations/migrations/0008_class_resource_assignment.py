from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0007_organization_academic"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0002_initial"),
        ("quiz", "0010_exam_created_by"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassResourceAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_type", models.CharField(choices=[("course", "Course"), ("track", "Exam Track"), ("exam", "Exam")], max_length=20)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="class_resource_assignments_created", to=settings.AUTH_USER_MODEL)),
                ("class_section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="resource_assignments", to="organizations.classsection")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_resource_assignments", to="organizations.organization")),
                ("course", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="class_resource_assignments", to="courses.course")),
                ("track", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="class_resource_assignments", to="quiz.examtrack")),
                ("exam", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="class_resource_assignments", to="quiz.exam")),
            ],
        ),
        migrations.AddConstraint(model_name="classresourceassignment", constraint=models.UniqueConstraint(fields=("class_section", "resource_type", "course", "track", "exam"), name="class_resource_assignment_unique")),
        migrations.AddIndex(model_name="classresourceassignment", index=models.Index(fields=["organization", "class_section", "is_active"], name="class_res_assign_scope_idx")),
    ]
