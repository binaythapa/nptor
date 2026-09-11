# payments/models.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PaymentOrder(models.Model):
    """Commercial order. Individual exams are not a sellable product."""

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

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_SUBSCRIPTION = "subscription"
    # Kept only so historical rows can still be loaded safely.
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPE_CHOICES = (
        (RESOURCE_COURSE, "Course"),
        (RESOURCE_TRACK, "Track"),
        (RESOURCE_SUBSCRIPTION, "All-access subscription"),
        (RESOURCE_EXAM, "Exam (legacy)"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_orders",
    )

    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

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

    subscription_plan = models.ForeignKey(
        "subscriptions.SubscriptionPlan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original price before applying any discount.",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total discount applied to this order.",
    )
    coupon = models.ForeignKey(
        "quiz.Coupon",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_orders",
    )
    currency = models.CharField(max_length=10, default="INR")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    gateway = models.CharField(max_length=50, blank=True, default="", db_index=True)
    gateway_order_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    gateway_payment_id = models.CharField(max_length=255, blank=True, default="", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["gateway", "gateway_order_id"]),
            models.Index(fields=["gateway", "gateway_payment_id"]),
        ]

    def clean(self):
        super().clean()

        resources = {
            self.RESOURCE_COURSE: self.course,
            self.RESOURCE_TRACK: self.track,
            self.RESOURCE_SUBSCRIPTION: self.subscription_plan,
            self.RESOURCE_EXAM: self.exam,
        }
        selected = resources.get(self.resource_type)
        if selected is None:
            raise ValidationError({"resource_type": "The selected resource must be provided."})

        for resource_type, resource in resources.items():
            if resource_type != self.resource_type and resource is not None:
                raise ValidationError({"resource_type": "Only one resource can be associated with an order."})

        if self.resource_type == self.RESOURCE_SUBSCRIPTION:
            if not self.subscription_plan.is_all_access():
                raise ValidationError({"subscription_plan": "Only all-access plans can be purchased as subscriptions."})

        if self.resource_type == self.RESOURCE_EXAM:
            raise ValidationError({"resource_type": "Individual exam purchases are no longer supported."})

        if self.amount is not None and self.amount < Decimal("0"):
            raise ValidationError({"amount": "Order amount cannot be negative."})
        if self.original_amount is not None and self.original_amount < Decimal("0"):
            raise ValidationError({"original_amount": "Original amount cannot be negative."})
        if self.discount_amount < Decimal("0"):
            raise ValidationError({"discount_amount": "Discount amount cannot be negative."})
        if self.original_amount is not None and self.discount_amount > self.original_amount:
            raise ValidationError({"discount_amount": "Discount cannot exceed original amount."})
        if self.original_amount is not None and self.amount is not None:
            if self.amount != self.original_amount - self.discount_amount:
                raise ValidationError({"amount": "Amount must equal original amount minus discount amount."})

    def get_resource(self):
        if self.resource_type == self.RESOURCE_COURSE:
            return self.course
        if self.resource_type == self.RESOURCE_TRACK:
            return self.track
        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam
        if self.resource_type == self.RESOURCE_SUBSCRIPTION:
            return self.subscription_plan
        return None

    def __str__(self):
        return f"{self.order_number} → {self.user} → {self.get_resource()}"


class PaymentTransaction(models.Model):
    """Record of a payment attempt. One order can have multiple attempts."""

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

    order = models.ForeignKey(
        PaymentOrder,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED, db_index=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True, default="", db_index=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["gateway_transaction_id"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} → {self.status}"
