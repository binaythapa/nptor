from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningActivityDismissal",
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
                ("resource_id", models.PositiveBigIntegerField()),
                ("dismissed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_activity_dismissals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-dismissed_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="learningactivitydismissal",
            constraint=models.UniqueConstraint(
                fields=("user", "resource_type", "resource_id"),
                name="uniq_learning_activity_dismissal",
            ),
        ),
        migrations.AddIndex(
            model_name="learningactivitydismissal",
            index=models.Index(
                fields=["user", "resource_type", "resource_id"],
                name="quiz_lad_user_type_id_idx",
            ),
        ),
    ]
