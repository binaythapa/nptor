# subscriptions/models/plan.py

from django.db import models

from django.core.validators import MinValueValidator


class SubscriptionPlan(models.Model):

    SCOPE_RESOURCE = "resource"
    SCOPE_ALL_ACCESS = "all_access"

    SCOPE_CHOICES = (
        (SCOPE_RESOURCE, "Resource"),
        (SCOPE_ALL_ACCESS, "All Access"),
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique internal identifier for this plan.",
    )

    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_RESOURCE,
        db_index=True,
        help_text="Resource plans are attached to courses/tracks; all-access plans unlock the whole platform.",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="NULL means lifetime access.",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
        ],
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["is_active"],
            ),
            models.Index(
                fields=["scope", "is_active"],
            ),
        ]

    def is_lifetime(self):
        return self.duration_days is None

    def is_all_access(self):
        return self.scope == self.SCOPE_ALL_ACCESS

    def __str__(self):
        return self.name
