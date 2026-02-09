from django.db import models
from core.models.subscription_base import BaseSubscription


class OrganizationCourseSubscription(BaseSubscription):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="course_subscriptions"
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="organization_subscriptions"
    )

    class Meta:
        unique_together = ("organization", "course")

    def __str__(self):
        return f"{self.organization} → {self.course}"
