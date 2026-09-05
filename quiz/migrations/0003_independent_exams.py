from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quiz", "0002_learningshortlist"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="exam",
            name="track",
        ),
        migrations.RemoveField(
            model_name="exam",
            name="prerequisite_exams",
        ),
        migrations.RemoveField(
            model_name="exam",
            name="is_free",
        ),
        migrations.RemoveField(
            model_name="exam",
            name="price",
        ),
        migrations.RemoveField(
            model_name="exam",
            name="currency",
        ),
        migrations.RemoveIndex(
            model_name="exam",
            name="exam_track_pub_idx",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="subscription_scope",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="pricing_type",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="monthly_price",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="lifetime_price",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="trial_days",
        ),
        migrations.RemoveField(
            model_name="examtrack",
            name="currency",
        ),
        migrations.CreateModel(
            name="TrackExam",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("position", models.PositiveIntegerField(default=1)),
                (
                    "exam",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="track_exams",
                        to="quiz.exam",
                    ),
                ),
                (
                    "track",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="track_exams",
                        to="quiz.examtrack",
                    ),
                ),
                (
                    "prerequisites",
                    models.ManyToManyField(
                        blank=True,
                        related_name="dependent_track_exams",
                        to="quiz.trackexam",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "indexes": [
                    models.Index(fields=["track", "position"], name="quiz_tracke_track_id_2a0a37_idx"),
                    models.Index(fields=["exam", "track"], name="quiz_tracke_exam_id_3c6e18_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("track", "exam"), name="unique_exam_per_track"),
                    models.UniqueConstraint(fields=("track", "position"), name="unique_track_exam_position"),
                ],
            },
        ),
    ]
