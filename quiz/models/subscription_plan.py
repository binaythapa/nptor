from django.db import models


class SubscriptionPlan(models.Model):
    """
    Admin-defined pricing & duration plans.
    """

    name = models.CharField(
        max_length=100
    )

    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="NULL = lifetime access",
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def is_lifetime(self):
        return self.duration_days is None

    def __str__(self):
        if self.duration_days:
            return (
                f"{self.name} "
                f"({self.duration_days} days)"
            )

        return f"{self.name} (Lifetime)"