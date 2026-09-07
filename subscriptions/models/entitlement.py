# subscriptions/models/entitlement.py

from django.core.exceptions import ValidationError
from django.db import models, transaction

from .subscription import Subscription


class SubscriptionEntitlement(models.Model):
    """Defines which resources are included in a subscription."""

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPE_CHOICES = (
        (RESOURCE_COURSE, "Course"),
        (RESOURCE_TRACK, "Exam Track"),
        (RESOURCE_EXAM, "Exam"),
    )

    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, db_index=True)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="entitlements",
    )
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
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["subscription", "is_active"], name="sub_ent_sub_active_idx"),
            models.Index(fields=["resource_type", "is_active"], name="sub_ent_type_active_idx"),
            models.Index(fields=["course"], name="sub_ent_course_idx"),
            models.Index(fields=["track"], name="sub_ent_track_idx"),
            models.Index(fields=["exam"], name="sub_ent_exam_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(resource_type="course", course__isnull=False, track__isnull=True, exam__isnull=True)
                    | models.Q(resource_type="track", course__isnull=True, track__isnull=False, exam__isnull=True)
                    | models.Q(resource_type="exam", course__isnull=True, track__isnull=True, exam__isnull=False)
                ),
                name="valid_subscription_entitlement_resource",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.resource_type not in {
            self.RESOURCE_COURSE,
            self.RESOURCE_TRACK,
            self.RESOURCE_EXAM,
        }:
            errors["resource_type"] = "Invalid subscription resource type."

        if self.resource_type == self.RESOURCE_COURSE:
            if not self.course:
                errors["course"] = "Course is required for a course entitlement."
            if self.track:
                errors["track"] = "Track must be empty for a course entitlement."
            if self.exam:
                errors["exam"] = "Exam must be empty for a course entitlement."
        elif self.resource_type == self.RESOURCE_TRACK:
            if not self.track:
                errors["track"] = "Exam track is required for a track entitlement."
            if self.course:
                errors["course"] = "Course must be empty for a track entitlement."
            if self.exam:
                errors["exam"] = "Exam must be empty for a track entitlement."
        elif self.resource_type == self.RESOURCE_EXAM:
            if not self.exam:
                errors["exam"] = "Exam is required for an exam entitlement."
            if self.course:
                errors["course"] = "Course must be empty for an exam entitlement."
            if self.track:
                errors["track"] = "Track must be empty for an exam entitlement."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Enforce one entitlement per subscription/resource on MySQL.

        The subscription row is locked before checking for a duplicate, which
        serializes entitlement creation/update for the same subscription.
        """
        self.full_clean()
        with transaction.atomic():
            Subscription.objects.select_for_update().get(pk=self.subscription_id)
            resource_field = {
                self.RESOURCE_COURSE: "course",
                self.RESOURCE_TRACK: "track",
                self.RESOURCE_EXAM: "exam",
            }[self.resource_type]
            duplicate = type(self).objects.filter(
                subscription_id=self.subscription_id,
                resource_type=self.resource_type,
                **{f"{resource_field}_id": getattr(self, f"{resource_field}_id")},
            ).exclude(pk=self.pk).exists()
            if duplicate:
                raise ValidationError(
                    "This resource is already included in the subscription."
                )
            return super().save(*args, **kwargs)

    def get_resource(self):
        if self.resource_type == self.RESOURCE_COURSE:
            return self.course
        if self.resource_type == self.RESOURCE_TRACK:
            return self.track
        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam
        return None

    def is_valid(self):
        if not self.is_active:
            return False
        if not self.get_resource():
            return False
        return self.subscription.is_valid()

    def activate(self):
        if not self.subscription.is_valid():
            raise ValidationError(
                "Cannot activate an entitlement for an invalid subscription."
            )
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def __str__(self):
        resource = self.get_resource()
        if resource:
            return f"{self.subscription} → {resource}"
        return f"{self.subscription} → Resource Entitlement"
