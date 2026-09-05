from django.conf import settings
from django.db import models


class LearningActivityDismissal(models.Model):
    """A student's choice to remove one resource from Learning Activity."""

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPES = (
        (RESOURCE_COURSE, "Course"),
        (RESOURCE_TRACK, "Exam Track"),
        (RESOURCE_EXAM, "Exam"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_activity_dismissals",
    )
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    resource_id = models.PositiveBigIntegerField()
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dismissed_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "resource_type", "resource_id"],
                name="uniq_learning_activity_dismissal",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.resource_type} → {self.resource_id}"
