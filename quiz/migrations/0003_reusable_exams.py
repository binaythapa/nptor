from django.db import migrations, models
import django.db.models.deletion


def migrate_exam_relationships(apps, schema_editor):
    Exam = apps.get_model("quiz", "Exam")
    ExamTrack = apps.get_model("quiz", "ExamTrack")
    TrackExam = apps.get_model("quiz", "TrackExam")

    # SubscriptionPlan belongs to an app without Django migrations in this
    # project, so use the runtime model for the data migration.
    from subscriptions.models import SubscriptionPlan

    exams = (
        Exam.objects
        .select_related("track")
        .prefetch_related("prerequisite_exams")
        .order_by("track_id", "created_at", "id")
    )

    order_by_track = {}

    for exam in exams:
        if not exam.track_id:
            continue

        order = order_by_track.get(exam.track_id, 0)
        order_by_track[exam.track_id] = order + 1

        track_exam, _ = TrackExam.objects.get_or_create(
            track_id=exam.track_id,
            exam_id=exam.id,
            defaults={"order": order},
        )

        prerequisites = list(exam.prerequisite_exams.all())
        if prerequisites:
            track_exam.prerequisite_exams.add(*prerequisites)

        # Preserve existing direct exam pricing as an explicit subscription
        # plan. Future pricing is no longer stored on Exam itself.
        if not exam.is_free and exam.price is not None:
            plan, _ = SubscriptionPlan.objects.get_or_create(
                code=f"exam-{exam.id}-direct",
                defaults={
                    "name": f"{exam.title} Direct Access",
                    "description": f"Direct access plan for {exam.title}",
                    "duration_days": None,
                    "price": exam.price,
                    "currency": exam.currency,
                    "is_active": True,
                },
            )
            exam.subscription_plans.add(plan)


def reverse_exam_relationships(apps, schema_editor):
    # The old Exam fields are intentionally removed by this migration. The
    # forward migration preserves their business data in TrackExam and
    # SubscriptionPlan, but there is no safe automatic reverse for those
    # normalized relationships.
    pass


class Migration(migrations.Migration):
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
                help_text="Optional plans that grant direct access to this exam.",
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
            index=models.Index(
                fields=["track", "order"],
                name="track_exam_order_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="trackexam",
            index=models.Index(
                fields=["exam"],
                name="track_exam_exam_idx",
            ),
        ),
        migrations.RunPython(
            migrate_exam_relationships,
            reverse_exam_relationships,
        ),
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
    ]
