from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0002_initial"),
        ("quiz", "0012_paymentrecord_commerce_targets"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseExam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0, help_text="Position of this exam in the course.")),
                ("is_required", models.BooleanField(default=True, help_text="Whether students must complete this exam as part of the course.")),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_exams", to="courses.course")),
                ("exam", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_memberships", to="quiz.exam")),
            ],
            options={
                "ordering": ["order", "id"],
                "indexes": [
                    models.Index(fields=["course", "order"], name="course_exam_order_idx"),
                    models.Index(fields=["exam"], name="course_exam_exam_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=["course", "exam"], name="unique_course_exam"),
                ],
            },
        ),
    ]
