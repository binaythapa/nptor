from django.core.exceptions import ValidationError
from django.db import models


class TrackExam(models.Model):
    """Place an independent exam inside a track.

    Ordering and prerequisites are properties of this relationship,
    allowing the same exam to be reused across multiple tracks.
    """

    track = models.ForeignKey(
        "ExamTrack",
        on_delete=models.CASCADE,
        related_name="track_exams",
    )

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
        related_name="track_exams",
    )

    position = models.PositiveIntegerField(default=1)

    prerequisites = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="dependent_track_exams",
    )

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["track", "exam"],
                name="unique_exam_per_track",
            ),
            models.UniqueConstraint(
                fields=["track", "position"],
                name="unique_track_exam_position",
            ),
        ]
        indexes = [
            models.Index(fields=["track", "position"]),
            models.Index(fields=["exam", "track"]),
        ]

    def clean(self):
        super().clean()
        if self.position <= 0:
            raise ValidationError({"position": "Position must be greater than zero."})

        if self.track_id and self.exam_id:
            if self.track.organization_id != self.exam.organization_id:
                raise ValidationError(
                    "Track and exam must belong to the same organization."
                )

        if self.pk:
            invalid = self.prerequisites.exclude(track_id=self.track_id).exists()
            if invalid:
                raise ValidationError(
                    "Prerequisites must belong to the same track."
                )

            if self.prerequisites.filter(pk=self.pk).exists():
                raise ValidationError(
                    "An exam cannot be its own prerequisite."
                )

    def __str__(self):
        return f"{self.track} → {self.exam}"
