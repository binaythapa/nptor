# payments/models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# ============================================================
# PAYMENT ORDER
# ============================================================


class PaymentOrder(models.Model):
    """
    Represents the commercial order created by a student.

    An order is NOT the same thing as a payment.

    Order:
        What the student is buying.

    Payment:
        How the order is being paid.
    """

    # =========================================================
    # ORDER STATUS
    # =========================================================

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_REFUNDED, "Refunded"),
    )

    # =========================================================
    # RESOURCE TYPE
    # =========================================================

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPE_CHOICES = (
        (RESOURCE_COURSE, "Course"),
        (RESOURCE_TRACK, "Track"),
        (RESOURCE_EXAM, "Exam"),
    )

    # =========================================================
    # USER
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )

    # =========================================================
    # ORDER NUMBER
    # =========================================================

    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    # =========================================================
    # RESOURCE
    # =========================================================

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
        db_index=True,
    )

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    # =========================================================
    # AMOUNT
    # =========================================================

    # Final amount actually payable/charged.
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # Original price before any coupon/discount.
    #
    # Nullable for backwards compatibility with existing orders.
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original price before applying any discount.",
    )

    # Coupon discount applied to this order.
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total discount applied to this order.",
    )

    # Coupon used for this order, if any.
    coupon = models.ForeignKey(
        "quiz.Coupon",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
        help_text="Coupon applied to this order, if any.",
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =========================================================
    # STATUS
    # =========================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # =========================================================
    # PAYMENT
    # =========================================================

    gateway = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
    )

    gateway_order_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
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
    # META
    # =========================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "gateway",
                    "gateway_order_id",
                ],
            ),
            models.Index(
                fields=[
                    "gateway",
                    "gateway_payment_id",
                ],
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        resources = {
            self.RESOURCE_COURSE: self.course,
            self.RESOURCE_TRACK: self.track,
            self.RESOURCE_EXAM: self.exam,
        }

        selected = resources.get(
            self.resource_type
        )

        if selected is None:
            raise ValidationError(
                {
                    "resource_type":
                        "The selected resource must be provided."
                }
            )

        for resource_type, resource in resources.items():

            if (
                resource_type != self.resource_type
                and resource is not None
            ):
                raise ValidationError(
                    {
                        "resource_type":
                            "Only one resource can be "
                            "associated with an order."
                    }
                )

        # -----------------------------------------------------
        # Pricing validation
        # -----------------------------------------------------

        if self.amount is not None and self.amount < Decimal("0"):
            raise ValidationError(
                {
                    "amount":
                        "Order amount cannot be negative."
                }
            )

        if (
            self.original_amount is not None
            and self.original_amount < Decimal("0")
        ):
            raise ValidationError(
                {
                    "original_amount":
                        "Original amount cannot be negative."
                }
            )

        if self.discount_amount < Decimal("0"):
            raise ValidationError(
                {
                    "discount_amount":
                        "Discount amount cannot be negative."
                }
            )

        if (
            self.original_amount is not None
            and self.discount_amount > self.original_amount
        ):
            raise ValidationError(
                {
                    "discount_amount":
                        "Discount cannot exceed original amount."
                }
            )

        if (
            self.original_amount is not None
            and self.amount is not None
        ):
            expected_amount = (
                self.original_amount
                - self.discount_amount
            )

            if self.amount != expected_amount:
                raise ValidationError(
                    {
                        "amount":
                            "Amount must equal original amount "
                            "minus discount amount."
                    }
                )

    # =========================================================
    # RESOURCE
    # =========================================================

    def get_resource(self):

        if self.resource_type == self.RESOURCE_COURSE:
            return self.course

        if self.resource_type == self.RESOURCE_TRACK:
            return self.track

        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam

        return None

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return (
            f"{self.order_number} → "
            f"{self.user} → "
            f"{self.get_resource()}"
        )


# ============================================================
# PAYMENT TRANSACTION
# ============================================================


class PaymentTransaction(models.Model):
    """
    Immutable-ish record of a payment attempt.

    One order can have multiple transactions.

    Example:

        Order
            ├── failed payment
            ├── failed payment
            └── successful payment
    """

    STATUS_CREATED = "created"
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = (
        (STATUS_CREATED, "Created"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    )

    # =========================================================
    # ORDER
    # =========================================================

    order = models.ForeignKey(
        PaymentOrder,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    # =========================================================
    # GATEWAY
    # =========================================================

    gateway = models.CharField(
        max_length=50,
        db_index=True,
    )

    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
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
    )

    # =========================================================
    # STATUS
    # =========================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        db_index=True,
    )

    # =========================================================
    # ERROR
    # =========================================================

    failure_reason = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # RAW GATEWAY RESPONSE
    # =========================================================

    raw_response = models.JSONField(
        default=dict,
        blank=True,
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

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "gateway",
                    "gateway_transaction_id",
                ]
            ),
            models.Index(
                fields=[
                    "order",
                    "status",
                ]
            ),
        ]

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        return (
            f"{self.gateway} → "
            f"{self.gateway_transaction_id or 'N/A'} → "
            f"{self.status}"
        )


# ============================================================
# PAYMENT WEBHOOK EVENT
# ============================================================


class PaymentWebhookEvent(models.Model):
    """
    Stores every gateway webhook/event.

    This is extremely important for:

        - idempotency
        - debugging
        - reconciliation
        - duplicate webhook protection
        - gateway disputes
    """

    # =========================================================
    # GATEWAY
    # =========================================================

    gateway = models.CharField(
        max_length=50,
        db_index=True,
    )

    event_id = models.CharField(
        max_length=255,
        db_index=True,
    )

    event_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =========================================================
    # PAYLOAD
    # =========================================================

    payload = models.JSONField(
        default=dict,
    )

    signature = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # PROCESSING
    # =========================================================

    processed = models.BooleanField(
        default=False,
        db_index=True,
    )

    processing_error = models.TextField(
        blank=True,
        default="",
    )

    # =========================================================
    # AUDIT
    # =========================================================

    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:

        ordering = ["-received_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "gateway",
                    "event_id",
                ],
                name="unique_payment_webhook_event",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "gateway",
                    "processed",
                ]
            ),
        ]

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        return (
            f"{self.gateway} → "
            f"{self.event_id} → "
            f"{self.event_type}"
        )