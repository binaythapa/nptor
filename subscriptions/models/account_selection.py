from django.core.exceptions import ValidationError
from django.db import models


class AccountSubscriptionSelection(models.Model):
    """A Course or Track selected under a limited Account subscription."""

    subscription = models.ForeignKey(
        "Subscription",
        on_delete=models.CASCADE,
        related_name="account_selections",
    )
    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="account_subscription_selections",
    )
    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="account_subscription_selections",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "course"],
                name="unique_account_subscription_course",
            ),
            models.UniqueConstraint(
                fields=["subscription", "track"],
                name="unique_account_subscription_track",
            ),
        ]
        indexes = [
            models.Index(fields=["subscription", "course"], name="acct_sel_sub_course_idx"),
            models.Index(fields=["subscription", "track"], name="acct_sel_sub_track_idx"),
        ]

    def clean(self):
        super().clean()
        if bool(self.course_id) == bool(self.track_id):
            raise ValidationError("Select exactly one Course or Track.")
        if self.subscription_id:
            if not self.subscription.plan.is_account_plan():
                raise ValidationError("Selections require an Account subscription plan.")
            if not self.subscription.is_user_subscription():
                raise ValidationError("Account subscriptions must belong to a user.")
            if not self.subscription.is_valid():
                raise ValidationError("Subscription is not currently valid.")

        if self.course_id and self.course.organization_id and self.subscription.user_id:
            pass

    def __str__(self):
        resource = self.course or self.track
        return f"{self.subscription} → {resource}"
