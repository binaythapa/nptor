from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0006_mysql_safe_primary_domain"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("is_current", models.BooleanField(default=False)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="academic_years", to="organizations.organization")),
            ],
            options={"ordering": ["-start_date", "name"]},
        ),
        migrations.CreateModel(
            name="OrganizationClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(blank=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classes", to="organizations.organization")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="OrganizationStudent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("student_id", models.CharField(blank=True, max_length=100)),
                ("admission_no", models.CharField(blank=True, max_length=100)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("guardian_name", models.CharField(blank=True, max_length=255)),
                ("guardian_phone", models.CharField(blank=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("graduated", "Graduated"), ("withdrawn", "Withdrawn")], default="active", max_length=20)),
                ("joined_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="students", to="organizations.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_student_records", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Guardian",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("relationship", models.CharField(blank=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="guardians", to="organizations.organization")),
            ],
        ),
        migrations.CreateModel(
            name="ClassSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50)),
                ("capacity", models.PositiveIntegerField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="organizations.academicyear")),
                ("class_group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="organizations.organizationclass")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_sections", to="organizations.organization")),
            ],
            options={"ordering": ["class_group__name", "name"]},
        ),
        migrations.CreateModel(
            name="StudentGuardian",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_primary", models.BooleanField(default=False)),
                ("can_receive_notifications", models.BooleanField(default=True)),
                ("guardian", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="student_links", to="organizations.guardian")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="guardian_links", to="organizations.organizationstudent")),
            ],
        ),
        migrations.CreateModel(
            name="StudentEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("roll_number", models.CharField(blank=True, max_length=50)),
                ("status", models.CharField(choices=[("active", "Active"), ("completed", "Completed"), ("transferred", "Transferred"), ("withdrawn", "Withdrawn")], default="active", max_length=20)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="organizations.academicyear")),
                ("class_section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="organizations.classsection")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="organizations.organizationstudent")),
            ],
        ),
        migrations.CreateModel(
            name="ClassTeacher",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=150)),
                ("is_primary", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_assignments", to="organizations.academicyear")),
                ("class_section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="teacher_assignments", to="organizations.classsection")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_teachers", to="organizations.organization")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_class_teachings", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(model_name="academicyear", constraint=models.UniqueConstraint(fields=("organization", "name"), name="org_academic_year_unique")),
        migrations.AddConstraint(model_name="organizationclass", constraint=models.UniqueConstraint(fields=("organization", "name"), name="org_class_name_unique")),
        migrations.AddConstraint(model_name="organizationstudent", constraint=models.UniqueConstraint(fields=("organization", "user"), name="org_student_user_unique")),
        migrations.AddConstraint(model_name="classsection", constraint=models.UniqueConstraint(fields=("academic_year", "class_group", "name"), name="academic_section_unique")),
        migrations.AddConstraint(model_name="studentguardian", constraint=models.UniqueConstraint(fields=("student", "guardian"), name="student_guardian_unique")),
        migrations.AddConstraint(model_name="classteacher", constraint=models.UniqueConstraint(fields=("teacher", "class_section", "subject"), name="class_teacher_subject_unique")),
        migrations.AddIndex(model_name="organizationstudent", index=models.Index(fields=["organization", "status"], name="org_student_status_idx")),
        migrations.AddIndex(model_name="organizationstudent", index=models.Index(fields=["organization", "student_id"], name="org_student_id_idx")),
        migrations.AddIndex(model_name="guardian", index=models.Index(fields=["organization", "name"], name="org_guardian_name_idx")),
        migrations.AddIndex(model_name="studentenrollment", index=models.Index(fields=["student", "academic_year", "status"], name="student_enrollment_status_idx")),
        migrations.AddIndex(model_name="studentenrollment", index=models.Index(fields=["class_section", "status"], name="section_enrollment_status_idx")),
        migrations.AddIndex(model_name="classteacher", index=models.Index(fields=["organization", "teacher", "is_active"], name="org_teacher_active_idx")),
    ]
