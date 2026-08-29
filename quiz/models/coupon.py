# quiz/models/coupon.py

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    """
    Promotional coupon used to reduce the price of a purchase.

    Coupon business rules are handled by:
        quiz.services.coupon_service.CouponService

    This model stores the coupon definition and aggregate usage count.
    Individual redemptions are stored in CouponRedemption.
    """

    # =========================================================
    # CORE
    # =========================================================

    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique coupon code.",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # =========================================================
    # DISCOUNT
    # =========================================================

    percent_off = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Percentage discount from 1 to 100.",
    )

    flat_off = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed discount amount.",
    )

    # =========================================================
    # APPLICABILITY
    # =========================================================

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="coupons",
        help_text="If set, coupon applies only to this course.",
    )

    track = models.ForeignKey(
        "ExamTrack",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="coupons",
        help_text="If set, coupon applies only to this track.",
    )

    exam = models.ForeignKey(
        "Exam",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="coupons",
        help_text="If set, coupon applies only to this exam.",
    )

    # =========================================================
    # VALIDITY
    # =========================================================

    valid_from = models.DateTimeField(
        db_index=True,
    )

    valid_to = models.DateTimeField(
        db_index=True,
    )

    # =========================================================
    # USAGE
    # =========================================================

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum total number of successful redemptions. "
            "Leave blank for unlimited usage."
        ),
    )

    used_count = models.PositiveIntegerField(
        default=0,
        editable=False,
        help_text="Number of successful redemptions.",
    )

    # =========================================================
    # TRIAL SUPPORT
    # =========================================================

    extra_trial_days = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Additional trial days granted when the coupon "
            "is successfully redeemed."
        ),
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
                fields=["is_active", "valid_from", "valid_to"],
                name="coupon_active_valid_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        # -----------------------------------------------------
        # Coupon code
        # -----------------------------------------------------

        if self.code:
            self.code = self.code.strip().upper()

        # -----------------------------------------------------
        # Discount: exactly one type
        # -----------------------------------------------------

        has_percent = self.percent_off is not None
        has_flat = self.flat_off is not None

        if has_percent == has_flat:
            raise ValidationError(
                "Exactly one of percent_off or flat_off must be set."
            )

        # -----------------------------------------------------
        # Percentage validation
        # -----------------------------------------------------

        if has_percent:
            if self.percent_off < 1:
                raise ValidationError(
                    {
                        "percent_off": (
                            "Percentage discount must be at least 1%."
                        )
                    }
                )

            if self.percent_off > 100:
                raise ValidationError(
                    {
                        "percent_off": (
                            "Percentage discount cannot exceed 100%."
                        )
                    }
                )

        # -----------------------------------------------------
        # Flat discount validation
        # -----------------------------------------------------

        if has_flat:
            if self.flat_off <= Decimal("0"):
                raise ValidationError(
                    {
                        "flat_off": (
                            "Flat discount must be greater than zero."
                        )
                    }
                )

        # -----------------------------------------------------
        # Validity period
        # -----------------------------------------------------

        if (
            self.valid_from
            and self.valid_to
            and self.valid_from >= self.valid_to
        ):
            raise ValidationError(
                {
                    "valid_to": (
                        "valid_to must be later than valid_from."
                    )
                }
            )

        # -----------------------------------------------------
        # Usage limit
        # -----------------------------------------------------

        if (
            self.usage_limit is not None
            and self.usage_limit < 1
        ):
            raise ValidationError(
                {
                    "usage_limit": (
                        "Usage limit must be at least 1."
                    )
                }
            )

        if (
            self.usage_limit is not None
            and self.used_count > self.usage_limit
        ):
            raise ValidationError(
                {
                    "used_count": (
                        "Used count cannot exceed the usage limit."
                    )
                }
            )

        # -----------------------------------------------------
        # Applicability
        #
        # No resource = global coupon.
        # One resource = resource-specific coupon.
        # -----------------------------------------------------

        resources = [
            self.course_id,
            self.track_id,
            self.exam_id,
        ]

        if sum(resource_id is not None for resource_id in resources) > 1:
            raise ValidationError(
                (
                    "A coupon can apply to only one resource: "
                    "course, track, or exam."
                )
            )

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        self.full_clean()

        return super().save(*args, **kwargs)

    # =========================================================
    # STATUS HELPERS
    # =========================================================

    def is_within_validity_period(self, at=None):
        """
        Return True when the coupon is within its configured
        validity window.
        """

        at = at or timezone.now()

        return (
            self.valid_from <= at <= self.valid_to
        )

    def has_usage_remaining(self):
        """
        Return True when the coupon still has available usage.
        """

        if self.usage_limit is None:
            return True

        return self.used_count < self.usage_limit

    def is_valid(self, at=None):
        """
        Basic coupon validity check.

        Resource and user-specific validation belongs in
        CouponService.
        """

        return (
            self.is_active
            and self.is_within_validity_period(at=at)
            and self.has_usage_remaining()
        )

    # =========================================================
    # APPLICABILITY HELPERS
    # =========================================================

    @property
    def is_global(self):
        return not any(
            (
                self.course_id,
                self.track_id,
                self.exam_id,
            )
        )

    def applies_to(
        self,
        *,
        course=None,
        track=None,
        exam=None,
    ):
        """
        Determine whether this coupon applies to the supplied
        purchase resource.

        A global coupon applies to any supported resource.

        A resource-specific coupon must match the corresponding
        resource.
        """

        if self.course_id:
            return (
                course is not None
                and course.pk == self.course_id
            )

        if self.track_id:
            return (
                track is not None
                and track.pk == self.track_id
            )

        if self.exam_id:
            return (
                exam is not None
                and exam.pk == self.exam_id
            )

        return True

    # =========================================================
    # DISCOUNT CALCULATION
    # =========================================================

    def calculate_discount(self, amount):
        """
        Calculate the discount amount.

        This is a pure calculation helper.

        CouponService remains responsible for deciding whether
        the coupon is actually valid and may be redeemed.
        """

        amount = Decimal(str(amount))

        if amount < Decimal("0"):
            raise ValidationError(
                "Purchase amount cannot be negative."
            )

        if self.percent_off is not None:
            discount = (
                amount
                * Decimal(self.percent_off)
                / Decimal("100")
            )
        elif self.flat_off is not None:
            discount = self.flat_off
        else:
            raise ValidationError(
                "Coupon has no valid discount configured."
            )

        # Never allow the discount to exceed the purchase price.
        discount = min(
            discount,
            amount,
        )

        return discount.quantize(
            Decimal("0.01")
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.code


class CouponRedemption(models.Model):
    """
    Immutable audit record of a successfully redeemed coupon.

    A redemption is created only after the associated purchase
    has successfully completed.
    """

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_redemptions",
    )

    # PaymentOrder is deliberately referenced as a string to avoid
    # importing the payments application at module import time.
    order = models.ForeignKey(
        "payments.PaymentOrder",
        on_delete=models.PROTECT,
        related_name="coupon_redemptions",
    )

    # =========================================================
    # FINANCIAL SNAPSHOT
    # =========================================================

    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # =========================================================
    # AUDIT
    # =========================================================

    redeemed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = ["-redeemed_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["coupon", "user", "order"],
                name="unique_coupon_user_order_redemption",
            ),
        ]

        indexes = [
            models.Index(
                fields=["coupon", "user"],
                name="coupon_redemption_user_idx",
            ),
            models.Index(
                fields=["user", "redeemed_at"],
                name="coupon_redemption_date_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        if self.original_amount < Decimal("0"):
            raise ValidationError(
                {
                    "original_amount": (
                        "Original amount cannot be negative."
                    )
                }
            )

        if self.discount_amount < Decimal("0"):
            raise ValidationError(
                {
                    "discount_amount": (
                        "Discount amount cannot be negative."
                    )
                }
            )

        if self.final_amount < Decimal("0"):
            raise ValidationError(
                {
                    "final_amount": (
                        "Final amount cannot be negative."
                    )
                }
            )

        if self.discount_amount > self.original_amount:
            raise ValidationError(
                {
                    "discount_amount": (
                        "Discount cannot exceed original amount."
                    )
                }
            )

        expected_final = (
            self.original_amount
            - self.discount_amount
        )

        if self.final_amount != expected_final:
            raise ValidationError(
                {
                    "final_amount": (
                        "Final amount must equal original amount "
                        "minus discount amount."
                    )
                }
            )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return (
            f"{self.coupon.code} → "
            f"{self.user} → "
            f"{self.order.order_number}"
        )