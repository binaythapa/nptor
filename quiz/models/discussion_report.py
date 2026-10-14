from django.conf import settings
from django.db import models


class DiscussionReport(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    discussion = models.ForeignKey(
        "QuestionDiscussion",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reason = models.CharField(
        max_length=255,
    )

    details = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = (
            "user",
            "discussion",
        )