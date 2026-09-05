from django.core.exceptions import ValidationError
from django.db import models


class TrackExam(models.Model):
    """Connect a reusable exam to a certification track.

    The relationship owns ordering, required status, and prerequisites so the
    same exam can safely participate in multiple tracks with different rules.
    """

    track = models.ForeignKey(
        "ExamTrack",
        on_delete=models.CASCADE,
        related_name="track_exams",
    )

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
        related_name="track_memberships",
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Position of this exam in the track.",
    )

    is_required = models.BooleanField(
        default=True,
        help_text="Whether students must complete this exam as part of the track.",
    )

    prerequisite_exams = models.ManyToManyField(
        "Exam",
        blank=True,
        related_name="track_prerequisite_memberships",
        help_text="Exams that must be passed before this track exam is available.",
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["track", "exam"],
                name="unique_track_exam",
            ),
        ]
        indexes = [
            models.Index(fields=["track", "order"], name="track_exam_order_idx"),
            models.Index(fields=["exam"], name="track_exam_exam_idx"),
        ]

    def clean(self):
        super().clean()

        if self.track_id and self.exam_id:
            track = self.track
            exam = self.exam
            if (
                track.organization_id is not None
                and exam.organization_id is not None
                and track.organization_id != exam.organization_id
            ):
                raise ValidationError(
                    {"exam": "Track and exam must belong to the same organization."}
                )

    def __str__(self):
        return f"{self.track} → {self.exam}"
