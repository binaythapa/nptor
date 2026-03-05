# organizations/models/subscription.py

from django.db import models
from core.models.subscription_base import BaseSubscription


class OrganizationCourseSubscription(BaseSubscription):

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="resource_subscriptions"
    )

    # Course
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions"
    )

    # Exam Track
    track = models.ForeignKey(
        "quiz.ExamTrack",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions"
    )

    # Exam
    exam = models.ForeignKey(
        "quiz.Exam",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "course"],
                name="unique_org_course_subscription",
            ),
            models.UniqueConstraint(
                fields=["organization", "track"],
                name="unique_org_track_subscription",
            ),
            models.UniqueConstraint(
                fields=["organization", "exam"],
                name="unique_org_exam_subscription",
            ),
        ]

    def __str__(self):

        if self.course:
            return f"{self.organization} → Course: {self.course}"

        if self.track:
            return f"{self.organization} → Track: {self.track}"

        if self.exam:
            return f"{self.organization} → Exam: {self.exam}"

        return f"{self.organization} → Resource"