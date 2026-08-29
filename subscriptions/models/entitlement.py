# subscriptions/models/entitlement.py

from django.core.exceptions import ValidationError
from django.db import models

from .subscription import Subscription


class SubscriptionEntitlement(models.Model):
    """
    Defines which resources are included in a subscription.

    IMPORTANT:

    SubscriptionEntitlement does NOT represent user access.

    It defines:

        Subscription
            ↓
        Entitlement
            ↓
        Course / Track / Exam

    Actual user access is represented by ResourceAccess.
    """

    # =========================================================
    # RESOURCE TYPES
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

    # =========================================================
    # RESOURCE TYPE
    # =========================================================

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
        db_index=True,
    )

    # =========================================================
    # SUBSCRIPTION
    # =========================================================

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="entitlements",
    )

    # =========================================================
    # RESOURCES
    # =========================================================

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscription_entitlements",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscription_entitlements",
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscription_entitlements",
    )

    # =========================================================
    # STATUS
    # =========================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # =========================================================
    # AUDIT
    # =========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "subscription",
                    "is_active",
                ],
                name="sub_ent_sub_active_idx",
            ),

            models.Index(
                fields=[
                    "resource_type",
                    "is_active",
                ],
                name="sub_ent_type_active_idx",
            ),

            models.Index(
                fields=[
                    "course",
                ],
                name="sub_ent_course_idx",
            ),

            models.Index(
                fields=[
                    "track",
                ],
                name="sub_ent_track_idx",
            ),

            models.Index(
                fields=[
                    "exam",
                ],
                name="sub_ent_exam_idx",
            ),
        ]

        constraints = [

            # =================================================
            # COURSE
            # =================================================

            models.UniqueConstraint(
                fields=[
                    "subscription",
                    "course",
                ],
                condition=models.Q(
                    resource_type="course",
                    course__isnull=False,
                ),
                name="unique_sub_course_entitlement",
            ),

            # =================================================
            # TRACK
            # =================================================

            models.UniqueConstraint(
                fields=[
                    "subscription",
                    "track",
                ],
                condition=models.Q(
                    resource_type="track",
                    track__isnull=False,
                ),
                name="unique_sub_track_entitlement",
            ),

            # =================================================
            # EXAM
            # =================================================

            models.UniqueConstraint(
                fields=[
                    "subscription",
                    "exam",
                ],
                condition=models.Q(
                    resource_type="exam",
                    exam__isnull=False,
                ),
                name="unique_sub_exam_entitlement",
            ),

            # =================================================
            # RESOURCE TYPE → RESOURCE
            # =================================================

            models.CheckConstraint(
                condition=(
                    models.Q(
                        resource_type="course",
                        course__isnull=False,
                        track__isnull=True,
                        exam__isnull=True,
                    )
                    |
                    models.Q(
                        resource_type="track",
                        course__isnull=True,
                        track__isnull=False,
                        exam__isnull=True,
                    )
                    |
                    models.Q(
                        resource_type="exam",
                        course__isnull=True,
                        track__isnull=True,
                        exam__isnull=False,
                    )
                ),
                name="valid_subscription_entitlement_resource",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        super().clean()

        errors = {}

        # -----------------------------------------------------
        # RESOURCE TYPE
        # -----------------------------------------------------

        if self.resource_type not in {
            self.RESOURCE_COURSE,
            self.RESOURCE_TRACK,
            self.RESOURCE_EXAM,
        }:
            errors["resource_type"] = (
                "Invalid subscription resource type."
            )

        # -----------------------------------------------------
        # COURSE
        # -----------------------------------------------------

        if self.resource_type == self.RESOURCE_COURSE:

            if not self.course:
                errors["course"] = (
                    "Course is required for a course entitlement."
                )

            if self.track:
                errors["track"] = (
                    "Track must be empty for a course entitlement."
                )

            if self.exam:
                errors["exam"] = (
                    "Exam must be empty for a course entitlement."
                )

        # -----------------------------------------------------
        # TRACK
        # -----------------------------------------------------

        elif self.resource_type == self.RESOURCE_TRACK:

            if not self.track:
                errors["track"] = (
                    "Exam track is required for a track entitlement."
                )

            if self.course:
                errors["course"] = (
                    "Course must be empty for a track entitlement."
                )

            if self.exam:
                errors["exam"] = (
                    "Exam must be empty for a track entitlement."
                )

        # -----------------------------------------------------
        # EXAM
        # -----------------------------------------------------

        elif self.resource_type == self.RESOURCE_EXAM:

            if not self.exam:
                errors["exam"] = (
                    "Exam is required for an exam entitlement."
                )

            if self.course:
                errors["course"] = (
                    "Course must be empty for an exam entitlement."
                )

            if self.track:
                errors["track"] = (
                    "Track must be empty for an exam entitlement."
                )

        if errors:
            raise ValidationError(errors)

    # =========================================================
    # RESOURCE
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
    # VALIDITY
    # =========================================================

    def is_valid(self):
        """
        An entitlement is valid only when:

        1. The entitlement is active.
        2. The parent subscription is valid.
        3. A valid resource is attached.
        """

        if not self.is_active:
            return False

        if not self.get_resource():
            return False

        return self.subscription.is_valid()

    # =========================================================
    # ACTIVATE
    # =========================================================

    def activate(self):

        if not self.subscription.is_valid():
            raise ValidationError(
                "Cannot activate an entitlement for "
                "an invalid subscription."
            )

        self.is_active = True

        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    # =========================================================
    # DEACTIVATE
    # =========================================================

    def deactivate(self):

        self.is_active = False

        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        resource = self.get_resource()

        if resource:
            return (
                f"{self.subscription} → "
                f"{resource}"
            )

        return (
            f"{self.subscription} → "
            f"Resource Entitlement"
        )