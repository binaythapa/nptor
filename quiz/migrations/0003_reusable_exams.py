from django.db import migrations, models
import django.db.models.deletion


def migrate_exam_relationships(apps, schema_editor):
    pass


def reverse_exam_relationships(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """
    Reusable-exam schema migration.

    This migration intentionally does not preserve existing exam data because
    the project is being reset during this architecture change. The existing
    migration history in local environments contains a separate legacy branch;
    this migration is based on the current main-line schema after 0002.
    """

    dependencies = [
        ("quiz", "0002_learningshortlist"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrackExam",
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
                    "order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Position of this exam in the track.",
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(
                        default=True,
                        help_text="Whether students must complete this exam as part of the track.",
                    ),
                ),
                (
                    "exam",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="track_memberships",
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
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddField(
            model_name="trackexam",
            name="prerequisite_exams",
            field=models.ManyToManyField(
                blank=True,
                help_text="Exams that must be passed before this track exam is available.",
                related_name="track_prerequisite_memberships",
                to="quiz.exam",
            ),
        ),
        migrations.AddField(
            model_name="exam",
            name="subscription_plans",
            field=models.ManyToManyField(
                blank=True,
                help_text="Optional plans that grant direct access to this reusable exam.",
                related_name="exams",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AddConstraint(
            model_name="trackexam",
            constraint=models.UniqueConstraint(
                fields=("track", "exam"),
                name="unique_track_exam",
            ),
        ),
        migrations.AddIndex(
            model_name="trackexam",
            index=models.Index(fields=["track", "order"], name="track_exam_order_idx"),
        ),
        migrations.AddIndex(
            model_name="trackexam",
            index=models.Index(fields=["exam"], name="track_exam_exam_idx"),
        ),
    ]