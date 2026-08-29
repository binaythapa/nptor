# organizations/models/subscription.py

from django.core.exceptions import ValidationError
from django.db import models

from core.models.subscription_base import BaseSubscription


class OrganizationCourseSubscription(BaseSubscription):

    # =========================================================
    # RESOURCE TYPE
    # =========================================================

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPE_CHOICES = (
        (
            RESOURCE_COURSE,
            "Course",
        ),
        (
            RESOURCE_TRACK,
            "Exam Track",
        ),
        (
            RESOURCE_EXAM,
            "Exam",
        ),
    )

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
        db_index=True,
    )

    # =========================================================
    # ORGANIZATION
    # =========================================================

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="resource_subscriptions",
    )

    # =========================================================
    # RESOURCES
    # =========================================================

    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions",
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="organization_subscriptions",
    )

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        resources = {
            self.RESOURCE_COURSE: self.course,
            self.RESOURCE_TRACK: self.track,
            self.RESOURCE_EXAM: self.exam,
        }

        selected_resource = resources.get(self.resource_type)

        if selected_resource is None:
            raise ValidationError(
                {
                    "resource_type": (
                        "The selected resource must be provided."
                    )
                }
            )

        for resource_type, resource in resources.items():

            if resource_type != self.resource_type and resource is not None:
                raise ValidationError(
                    {
                        "resource_type": (
                            "Only one resource type can be associated "
                            "with a subscription."
                        )
                    }
                )

    # =========================================================
    # RESOURCE HELPER
    # =========================================================

    def get_resource(self):
        if self.resource_type == self.RESOURCE_COURSE:
            return self.course

        if self.resource_type == self.RESOURCE_TRACK:
            return self.track

        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam

        return None

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        resource = self.get_resource()

        if resource:
            return (
                f"{self.organization} → "
                f"{resource}"
            )

        return (
            f"{self.organization} → "
            f"Resource Subscription"
        )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "organization",
                    "resource_type",
                ]
            ),
            models.Index(
                fields=[
                    "organization",
                    "expires_at",
                ]
            ),
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "organization",
                    "course",
                ],
                name="unique_org_course_subscription",
            ),

            models.UniqueConstraint(
                fields=[
                    "organization",
                    "track",
                ],
                name="unique_org_track_subscription",
            ),

            models.UniqueConstraint(
                fields=[
                    "organization",
                    "exam",
                ],
                name="unique_org_exam_subscription",
            ),
        ]