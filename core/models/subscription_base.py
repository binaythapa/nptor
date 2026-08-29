# core/models/subscription_base.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class BaseSubscription(models.Model):
    """
    Abstract base model for all subscription types.

    This model intentionally knows nothing about:
        - User
        - Organization
        - Course
        - Exam
        - Track

    Concrete subscription models should define ownership
    and the actual resource being subscribed to.
    """

    # =========================================================
    # SUBSCRIPTION STATUS
    # =========================================================

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_SUSPENDED, "Suspended"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    # =========================================================
    # SUBSCRIPTION DATES
    # =========================================================

    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the subscription was created.",
    )

    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When access becomes valid.",
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When access expires. NULL means no expiry.",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # LEGACY / COMPATIBILITY FLAG
    # =========================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Legacy compatibility flag. New business logic should "
            "prefer status and is_valid()."
        ),
    )

    # =========================================================
    # BILLING
    # =========================================================

    payment_required = models.BooleanField(
        default=False,
    )

    payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =========================================================
    # PAYMENT STATUS
    # =========================================================

    PAYMENT_NOT_REQUIRED = "not_required"
    PAYMENT_PENDING = "pending"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_REFUNDED = "refunded"

    PAYMENT_STATUS_CHOICES = (
        (
            PAYMENT_NOT_REQUIRED,
            "Not Required",
        ),
        (
            PAYMENT_PENDING,
            "Pending",
        ),
        (
            PAYMENT_PAID,
            "Paid",
        ),
        (
            PAYMENT_FAILED,
            "Failed",
        ),
        (
            PAYMENT_REFUNDED,
            "Refunded",
        ),
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_NOT_REQUIRED,
        db_index=True,
    )

    # =========================================================
    # ADMIN / MANUAL SUBSCRIPTION
    # =========================================================

    subscribed_by_admin = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that the subscription was granted manually "
            "by an administrator."
        ),
    )

    # =========================================================
    # AUTO RENEWAL
    # =========================================================

    auto_renew = models.BooleanField(
        default=False,
    )

    # =========================================================
    # CANCELLATION
    # =========================================================

    cancellation_reason = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # INTERNAL NOTES
    # =========================================================

    notes = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        abstract = True

    # =========================================================
    # MODEL VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        if self.amount is not None:
            if self.amount < Decimal("0.00"):
                raise ValidationError(
                    {
                        "amount": "Amount cannot be negative."
                    }
                )

        if self.expires_at and self.starts_at:
            if self.expires_at <= self.starts_at:
                raise ValidationError(
                    {
                        "expires_at": (
                            "Expiration time must be later "
                            "than start time."
                        )
                    }
                )

        if self.cancelled_at and self.status != self.STATUS_CANCELLED:
            raise ValidationError(
                {
                    "cancelled_at": (
                        "Cancelled subscriptions must have "
                        "status='cancelled'."
                    )
                }
            )

        if self.status == self.STATUS_CANCELLED and not self.cancelled_at:
            raise ValidationError(
                {
                    "cancelled_at": (
                        "Cancelled subscriptions must have "
                        "a cancellation timestamp."
                    )
                }
            )

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):
        """
        Keep legacy is_active synchronized with the lifecycle status.

        Existing code may still check is_active, so we preserve it
        while making status the primary lifecycle indicator.
        """

        if self.status in (
            self.STATUS_CANCELLED,
            self.STATUS_EXPIRED,
            self.STATUS_SUSPENDED,
        ):
            self.is_active = False

        elif self.status == self.STATUS_ACTIVE:
            self.is_active = True

        self.full_clean()

        super().save(*args, **kwargs)

    # =========================================================
    # DATE HELPERS
    # =========================================================

    def has_started(self):
        """
        Returns True when the subscription has reached its start time.
        """

        now = timezone.now()

        if self.starts_at is None:
            return True

        return now >= self.starts_at

    def has_expired(self):
        """
        Returns True when the subscription has passed its expiry time.
        """

        if self.expires_at is None:
            return False

        return timezone.now() >= self.expires_at

    # =========================================================
    # VALIDITY
    # =========================================================

    def is_valid(self):
        """
        Determines whether the subscription currently grants access.

        This is the primary method that application code should use.
        """

        if self.status != self.STATUS_ACTIVE:
            return False

        if not self.is_active:
            return False

        if not self.has_started():
            return False

        if self.has_expired():
            return False

        return True

    # =========================================================
    # LIFECYCLE HELPERS
    # =========================================================

    def activate(self):
        """
        Activate the subscription.
        """

        self.status = self.STATUS_ACTIVE
        self.is_active = True

        if self.starts_at is None:
            self.starts_at = timezone.now()

        self.cancelled_at = None
        self.cancellation_reason = ""

        self.save()

    def suspend(self):
        """
        Temporarily suspend the subscription.
        """

        self.status = self.STATUS_SUSPENDED
        self.is_active = False

        self.save()

    def cancel(self, reason=""):
        """
        Cancel the subscription.
        """

        self.status = self.STATUS_CANCELLED
        self.is_active = False
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason or ""

        self.save()

    def mark_expired(self):
        """
        Explicitly mark the subscription as expired.
        """

        self.status = self.STATUS_EXPIRED
        self.is_active = False

        self.save()

    # =========================================================
    # DISPLAY HELPERS
    # =========================================================

    @property
    def is_expiring(self):
        """
        Returns True when the subscription expires within 7 days.
        """

        if not self.expires_at:
            return False

        if self.status != self.STATUS_ACTIVE:
            return False

        now = timezone.now()

        return (
            now <= self.expires_at
            <= now + timezone.timedelta(days=7)
        )

    @property
    def days_remaining(self):
        """
        Number of whole days remaining.

        Returns:
            None for unlimited subscriptions.
            0 or greater for subscriptions with expiry.
        """

        if not self.expires_at:
            return None

        remaining = self.expires_at - timezone.now()

        if remaining.total_seconds() <= 0:
            return 0

        return remaining.days