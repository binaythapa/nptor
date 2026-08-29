# subscriptions/models/plan.py

from django.db import models

from django.core.validators import MinValueValidator


class SubscriptionPlan(models.Model):

    name = models.CharField(
        max_length=100,
    )

    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique internal identifier for this plan.",
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
        ]

    def is_lifetime(self):
        return self.duration_days is None

    def __str__(self):
        return self.name