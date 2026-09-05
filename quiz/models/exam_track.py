from django.core.exceptions import ValidationError
from django.db import models


class ExamTrack(models.Model):
    """A purchasable learning product composed of independent exams."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(help_text="Unique inside organization")
    description = models.TextField(blank=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exam_tracks",
    )

    subscription_plans = models.ManyToManyField(
        "subscriptions.SubscriptionPlan",
        blank=True,
        related_name="exam_tracks",
        help_text="Dynamic pricing plans available for this track",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

    def has_dynamic_plans(self):
        return self.subscription_plans.filter(is_active=True).exists()

    def is_free(self):
        return not self.has_dynamic_plans()

    def __str__(self):
        if self.organization:
            return f"{self.organization.name} → {self.title}"
        return self.title
