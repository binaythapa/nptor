from django.db import models
from django.utils import timezone


class BaseSubscription(models.Model):
    is_active = models.BooleanField(default=True)

    subscribed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Payment / billing
    payment_required = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(max_length=10, default="INR")

    subscribed_by_admin = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
