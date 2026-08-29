from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Payment(models.Model):
    """
    Represents a financial transaction related to a subscription.

    One subscription can have multiple payments over its lifetime.

    Example:

        Subscription
            ├── Initial payment
            ├── Renewal payment
            └── Renewal payment
    """

    # =========================================================
    # PAYMENT STATUS
    # =========================================================

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_PARTIALLY_REFUNDED = "partially_refunded"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Successful"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_PARTIALLY_REFUNDED, "Partially Refunded"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # =========================================================
    # SUBSCRIPTION
    # =========================================================

    subscription = models.ForeignKey(
        "subscriptions.Subscription",
        on_delete=models.PROTECT,
        related_name="payments",
    )

    # =========================================================
    # AMOUNT
    # =========================================================

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =========================================================
    # PAYMENT PROVIDER
    # =========================================================

    PROVIDER_MANUAL = "manual"
    PROVIDER_RAZORPAY = "razorpay"
    PROVIDER_STRIPE = "stripe"
    PROVIDER_OTHER = "other"

    PROVIDER_CHOICES = (
        (PROVIDER_MANUAL, "Manual"),
        (PROVIDER_RAZORPAY, "Razorpay"),
        (PROVIDER_STRIPE, "Stripe"),
        (PROVIDER_OTHER, "Other"),
    )

    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_MANUAL,
        db_index=True,
    )

    # Provider's transaction/payment ID.
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    # Provider's order ID, if applicable.
    order_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    # =========================================================
    # REFUND
    # =========================================================

    refunded_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    refund_reference = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    # =========================================================
    # WHO INITIATED PAYMENT
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_payments",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_payments",
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

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # NOTES
    # =========================================================

    notes = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "subscription",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "provider",
                    "transaction_id",
                ],
            ),
            models.Index(
                fields=[
                    "organization",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "user",
                    "status",
                ],
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        if self.amount < 0:
            raise ValidationError(
                {
                    "amount": "Payment amount cannot be negative."
                }
            )

        if self.refunded_amount < 0:
            raise ValidationError(
                {
                    "refunded_amount": (
                        "Refunded amount cannot be negative."
                    )
                }
            )

        if self.refunded_amount > self.amount:
            raise ValidationError(
                {
                    "refunded_amount": (
                        "Refunded amount cannot exceed "
                        "the payment amount."
                    )
                }
            )

        if self.status == self.STATUS_REFUNDED:
            if self.refunded_amount != self.amount:
                raise ValidationError(
                    {
                        "refunded_amount": (
                            "A fully refunded payment must have "
                            "the full amount refunded."
                        )
                    }
                )

        if self.status == self.STATUS_PARTIALLY_REFUNDED:
            if not (
                0 < self.refunded_amount < self.amount
            ):
                raise ValidationError(
                    {
                        "refunded_amount": (
                            "A partially refunded payment must "
                            "have a refund amount between 0 "
                            "and the original payment amount."
                        )
                    }
                )

    # =========================================================
    # HELPERS
    # =========================================================

    def is_successful(self):
        return self.status == self.STATUS_SUCCESS

    def is_refunded(self):
        return self.status in (
            self.STATUS_REFUNDED,
            self.STATUS_PARTIALLY_REFUNDED,
        )

    @property
    def refundable_amount(self):
        return self.amount - self.refunded_amount

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return (
            f"{self.provider} - "
            f"{self.amount} {self.currency} - "
            f"{self.get_status_display()}"
        )