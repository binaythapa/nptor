from django.contrib.auth.models import User
from django.db import models

from core.models.subscription_base import BaseSubscription


class ExamSubscription(BaseSubscription):
    """
    Represents user's access permission to an exam.

    This is:
    - NOT an exam attempt
    - NOT an unlock by passing
    - The foundation for paid exam access
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exam_subscriptions",
    )

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    class Meta:
        unique_together = ("user", "exam")

        indexes = [
            models.Index(
                fields=["user", "exam"]
            ),
            models.Index(
                fields=["is_active"]
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.exam}"