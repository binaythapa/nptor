from django.db import models
from django.conf import settings

from core.models.subscription_base import BaseSubscription
from courses.models import Course   # ⚠️ IMPORTANT: correct import


class CourseSubscription(BaseSubscription):
    """
    Grants a user time-bound access to a course.
    Source indicates who granted the subscription.
    """

    SOURCE_CHOICES = (
        ("quiz", "Quiz"),
        ("organization", "Organization"),
        ("admin", "Admin"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_subscriptions",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="quiz",   # 👈 IMPORTANT (avoid NULL issues)
    )

    class Meta:
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.course} ({self.source})"
