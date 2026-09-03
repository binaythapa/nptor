from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("courses", "0002_initial"),
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningShortlist",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("course", "Course"),
                            ("track", "Exam Track"),
                            ("exam", "Exam"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_shortlists",
                        to="courses.course",
                    ),
                ),
                (
                    "exam",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_shortlists",
                        to="quiz.exam",
                    ),
                ),
                (
                    "track",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_shortlists",
                        to="quiz.examtrack",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_shortlist",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="learningshortlist",
            constraint=models.UniqueConstraint(
                condition=Q(resource_type="course"),
                fields=("user", "resource_type", "course"),
                name="uniq_shortlist_user_course",
            ),
        ),
        migrations.AddConstraint(
            model_name="learningshortlist",
            constraint=models.UniqueConstraint(
                condition=Q(resource_type="track"),
                fields=("user", "resource_type", "track"),
                name="uniq_shortlist_user_track",
            ),
        ),
        migrations.AddConstraint(
            model_name="learningshortlist",
            constraint=models.UniqueConstraint(
                condition=Q(resource_type="exam"),
                fields=("user", "resource_type", "exam"),
                name="uniq_shortlist_user_exam",
            ),
        ),
    ]
