from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .plan import SubscriptionPlan


class Subscription(models.Model):
    """
    Represents an actual subscription purchased or granted to
    either an individual user or an organization.

    Subscription defines:
        - owner
        - plan
        - billing
        - lifecycle
        - start / expiry

    Resource-specific access is handled separately through
    SubscriptionEntitlement and ResourceAccess.
    """

    # =========================================================
    # STATUS
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
    # PLAN
    # =========================================================

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    # =========================================================
    # OWNER
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    # =========================================================
    # DATES
    # =========================================================

    subscribed_at = models.DateTimeField(
        auto_now_add=True,
    )

    starts_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # BILLING
    # =========================================================

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=(
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ),
        default="not_required",
        db_index=True,
    )

    payment_id = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    # =========================================================
    # ADMIN / MANUAL GRANT
    # =========================================================

    subscribed_by_admin = models.BooleanField(
        default=False,
        db_index=True,
    )

    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions_granted",
    )

    # =========================================================
    # RENEWAL
    # =========================================================

    auto_renew = models.BooleanField(
        default=False,
    )

    # =========================================================
    # NOTES
    # =========================================================

    cancellation_reason = models.TextField(
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
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
                    "user",
                    "status",
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
                    "plan",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "expires_at",
                    "status",
                ],
            ),
        ]

        constraints = [

            # -------------------------------------------------
            # Exactly one owner
            # -------------------------------------------------

            models.CheckConstraint(
                condition=(
                    models.Q(
                        user__isnull=False,
                        organization__isnull=True,
                    )
                    |
                    models.Q(
                        user__isnull=True,
                        organization__isnull=False,
                    )
                ),
                name="subscription_exactly_one_owner",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):

        super().clean()

        # -----------------------------------------------------
        # Exactly one owner
        # -----------------------------------------------------

        if self.user_id and self.organization_id:
            raise ValidationError(
                "A subscription cannot belong to both "
                "a user and an organization."
            )

        if not self.user_id and not self.organization_id:
            raise ValidationError(
                "A subscription must belong to either "
                "a user or an organization."
            )

        # -----------------------------------------------------
        # Date validation
        # -----------------------------------------------------

        if self.expires_at and self.starts_at:

            if self.expires_at <= self.starts_at:
                raise ValidationError(
                    {
                        "expires_at": (
                            "Expiration time must be later "
                            "than the start time."
                        )
                    }
                )

        # -----------------------------------------------------
        # Cancellation validation
        # -----------------------------------------------------

        if self.status == self.STATUS_CANCELLED:

            if not self.cancelled_at:
                raise ValidationError(
                    {
                        "cancelled_at": (
                            "Cancelled subscriptions must "
                            "have a cancellation timestamp."
                        )
                    }
                )

    # =========================================================
    # STARTED
    # =========================================================

    def has_started(self):

        return timezone.now() >= self.starts_at

    # =========================================================
    # EXPIRED
    # =========================================================

    def has_expired(self):

        if self.expires_at is None:
            return False

        return timezone.now() >= self.expires_at

    # =========================================================
    # VALIDITY
    # =========================================================

    def is_valid(self):
        """
        Return True only when the subscription can currently
        provide access.
        """

        if self.status != self.STATUS_ACTIVE:
            return False

        if not self.has_started():
            return False

        if self.has_expired():
            return False

        return True

    # =========================================================
    # ACTIVATE
    # =========================================================

    def activate(self):

        self.status = self.STATUS_ACTIVE
        self.cancelled_at = None
        self.cancellation_reason = ""

        self.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )

    # =========================================================
    # SUSPEND
    # =========================================================

    def suspend(self):

        self.status = self.STATUS_SUSPENDED

        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    # =========================================================
    # CANCEL
    # =========================================================

    def cancel(
        self,
        reason="",
    ):

        self.status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason or ""

        self.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )

    # =========================================================
    # EXPIRE
    # =========================================================

    def mark_expired(self):

        self.status = self.STATUS_EXPIRED

        self.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    # =========================================================
    # OWNER HELPERS
    # =========================================================

    def is_user_subscription(self):

        return self.user_id is not None

    def is_organization_subscription(self):

        return self.organization_id is not None

    # =========================================================
    # OWNER
    # =========================================================

    def get_owner(self):

        return self.user or self.organization

    # =========================================================
    # DISPLAY
    # =========================================================

    def __str__(self):

        owner = self.get_owner()

        return (
            f"{owner} → "
            f"{self.plan.name} "
            f"({self.get_status_display()})"
        )