from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.subscription_base import BaseSubscription


class ExamTrackSubscription(BaseSubscription):
    """
    Represents a user's access to an ExamTrack.

    A track subscription unlocks all exams belonging
    to that track.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="organization_track_subscriptions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="track_subscriptions",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    is_trial = models.BooleanField(
        default=False,
    )

    class Meta:
        unique_together = (
            "user",
            "track",
        )

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "track",
                ]
            ),
            models.Index(
                fields=[
                    "is_active",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.track}"

    def days_remaining(self):
        if not self.expires_at:
            return None

        return max(
            (
                self.expires_at
                - timezone.now()
            ).days,
            0,
        )