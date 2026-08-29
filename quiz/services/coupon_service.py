# quiz/services/coupon_service.py

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from quiz.models import Coupon, CouponRedemption


# ============================================================
# EXCEPTIONS
# ============================================================


class CouponError(Exception):
    """Base exception for coupon-related errors."""


class InvalidCouponError(CouponError):
    """Raised when a coupon does not exist or is invalid."""


class CouponNotApplicableError(CouponError):
    """Raised when a coupon does not apply to the resource."""


class CouponUsageLimitError(CouponError):
    """Raised when a coupon has reached its usage limit."""


class CouponAlreadyRedeemedError(CouponError):
    """Raised when a coupon redemption already exists for an order."""


# ============================================================
# SERVICE
# ============================================================


class CouponService:
    """
    Centralized coupon business logic.

    Responsibilities:

        1. Normalize coupon codes
        2. Validate coupon status
        3. Validate validity period
        4. Validate usage limit
        5. Validate resource applicability
        6. Calculate discounts
        7. Redeem coupons safely
        8. Maintain CouponRedemption history

    Important:

        Applying/validating a coupon DOES NOT increment used_count.

        used_count is incremented only when the coupon is
        successfully redeemed after the associated payment
        succeeds.
    """

    # ========================================================
    # CODE NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize_code(code):
        """
        Normalize a coupon code.

        Example:

            " save100 " → "SAVE100"
        """

        if code is None:
            return ""

        return str(code).strip().upper()

    # ========================================================
    # GET COUPON
    # ========================================================

    @classmethod
    def get_coupon(cls, code):
        """
        Return the coupon matching the supplied code.

        Returns:
            Coupon

        Raises:
            InvalidCouponError
        """

        normalized_code = cls.normalize_code(code)

        if not normalized_code:
            raise InvalidCouponError(
                "Coupon code is required."
            )

        try:
            return Coupon.objects.get(
                code=normalized_code
            )
        except Coupon.DoesNotExist:
            raise InvalidCouponError(
                "Invalid coupon code."
            )

    # ========================================================
    # VALIDATE COUPON
    # ========================================================

    @classmethod
    def validate_coupon(
        cls,
        code,
        *,
        course=None,
        track=None,
        exam=None,
        at=None,
    ):
        """
        Validate a coupon against the supplied resource.

        Returns:

            Coupon

        Raises:

            InvalidCouponError
            CouponNotApplicableError
            CouponUsageLimitError
        """

        coupon = cls.get_coupon(code)

        now = at or timezone.now()

        # ----------------------------------------------------
        # Active
        # ----------------------------------------------------

        if not coupon.is_active:
            raise InvalidCouponError(
                "Coupon is inactive."
            )

        # ----------------------------------------------------
        # Validity period
        # ----------------------------------------------------

        if coupon.valid_from > now:
            raise InvalidCouponError(
                "Coupon is not active yet."
            )

        if coupon.valid_to < now:
            raise InvalidCouponError(
                "Coupon has expired."
            )

        # ----------------------------------------------------
        # Usage limit
        # ----------------------------------------------------

        if (
            coupon.usage_limit is not None
            and coupon.used_count >= coupon.usage_limit
        ):
            raise CouponUsageLimitError(
                "Coupon usage limit has been reached."
            )

        # ----------------------------------------------------
        # Resource applicability
        # ----------------------------------------------------

        if not coupon.applies_to(
            course=course,
            track=track,
            exam=exam,
        ):
            raise CouponNotApplicableError(
                "Coupon is not applicable to this resource."
            )

        return coupon

    # ========================================================
    # VALIDATE WITHOUT EXCEPTIONS
    # ========================================================

    @classmethod
    def check_coupon(
        cls,
        code,
        *,
        course=None,
        track=None,
        exam=None,
        at=None,
    ):
        """
        User-interface friendly validation.

        Returns:

            (coupon, None)

        or:

            (None, error_message)
        """

        try:
            coupon = cls.validate_coupon(
                code,
                course=course,
                track=track,
                exam=exam,
                at=at,
            )

            return coupon, None

        except CouponError as exc:
            return None, str(exc)

    # ========================================================
    # CALCULATE DISCOUNT
    # ========================================================

    @classmethod
    def calculate_discount(
        cls,
        coupon,
        amount,
    ):
        """
        Calculate the discount for a validated coupon.

        Returns:

            Decimal

        The discount can never exceed the purchase amount.
        """

        if not isinstance(coupon, Coupon):
            raise ValidationError(
                "A valid Coupon instance is required."
            )

        try:
            amount = Decimal(str(amount))
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            raise ValidationError(
                "Invalid purchase amount."
            )

        if amount < Decimal("0.00"):
            raise ValidationError(
                "Purchase amount cannot be negative."
            )

        discount = coupon.calculate_discount(
            amount
        )

        return discount.quantize(
            Decimal("0.01")
        )

    # ========================================================
    # CALCULATE FINAL PRICE
    # ========================================================

    @classmethod
    def calculate_price(
        cls,
        amount,
        coupon=None,
    ):
        """
        Calculate the complete pricing breakdown.

        Returns:

            {
                "original_amount": Decimal,
                "discount_amount": Decimal,
                "final_amount": Decimal,
            }
        """

        try:
            original_amount = Decimal(
                str(amount)
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            raise ValidationError(
                "Invalid purchase amount."
            )

        if original_amount < Decimal("0.00"):
            raise ValidationError(
                "Purchase amount cannot be negative."
            )

        discount_amount = Decimal("0.00")

        if coupon is not None:
            discount_amount = cls.calculate_discount(
                coupon,
                original_amount,
            )

        final_amount = (
            original_amount
            - discount_amount
        )

        if final_amount < Decimal("0.00"):
            final_amount = Decimal("0.00")

        return {
            "original_amount": original_amount.quantize(
                Decimal("0.01")
            ),
            "discount_amount": discount_amount.quantize(
                Decimal("0.01")
            ),
            "final_amount": final_amount.quantize(
                Decimal("0.01")
            ),
        }

    # ========================================================
    # REDEEM COUPON
    # ========================================================

    @classmethod
    @transaction.atomic
    def redeem(
        cls,
        coupon,
        *,
        user,
        order,
        original_amount,
        discount_amount,
        final_amount,
    ):
        """
        Redeem a coupon after successful payment.

        This operation is atomic.

        The coupon row is locked using select_for_update()
        so concurrent successful payments cannot both consume
        the same final available coupon slot.

        Returns:

            CouponRedemption
        """

        if not isinstance(coupon, Coupon):
            raise ValidationError(
                "A valid Coupon instance is required."
            )

        if not user or not user.is_authenticated:
            raise ValidationError(
                "Authenticated user is required."
            )

        if not order:
            raise ValidationError(
                "Payment order is required."
            )

        # ----------------------------------------------------
        # Lock coupon row
        # ----------------------------------------------------

        locked_coupon = (
            Coupon.objects
            .select_for_update()
            .get(pk=coupon.pk)
        )

        now = timezone.now()

        # ----------------------------------------------------
        # Revalidate while holding the lock
        # ----------------------------------------------------

        if not locked_coupon.is_active:
            raise InvalidCouponError(
                "Coupon is inactive."
            )

        if locked_coupon.valid_from > now:
            raise InvalidCouponError(
                "Coupon is not active yet."
            )

        if locked_coupon.valid_to < now:
            raise InvalidCouponError(
                "Coupon has expired."
            )

        if (
            locked_coupon.usage_limit is not None
            and locked_coupon.used_count
            >= locked_coupon.usage_limit
        ):
            raise CouponUsageLimitError(
                "Coupon usage limit has been reached."
            )

        # ----------------------------------------------------
        # Verify order ownership
        # ----------------------------------------------------

        if order.user_id != user.id:
            raise ValidationError(
                "The payment order does not belong to this user."
            )

        # ----------------------------------------------------
        # Verify coupon belongs to order
        # ----------------------------------------------------

        if order.coupon_id != locked_coupon.id:
            raise ValidationError(
                "The coupon is not associated with this order."
            )

        # ----------------------------------------------------
        # Normalize financial values
        # ----------------------------------------------------

        try:
            original_amount = Decimal(
                str(original_amount)
            ).quantize(Decimal("0.01"))

            discount_amount = Decimal(
                str(discount_amount)
            ).quantize(Decimal("0.01"))

            final_amount = Decimal(
                str(final_amount)
            ).quantize(Decimal("0.01"))

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            raise ValidationError(
                "Invalid coupon redemption amounts."
            )

        # ----------------------------------------------------
        # Financial validation
        # ----------------------------------------------------

        if original_amount < Decimal("0.00"):
            raise ValidationError(
                "Original amount cannot be negative."
            )

        if discount_amount < Decimal("0.00"):
            raise ValidationError(
                "Discount amount cannot be negative."
            )

        if final_amount < Decimal("0.00"):
            raise ValidationError(
                "Final amount cannot be negative."
            )

        if discount_amount > original_amount:
            raise ValidationError(
                "Discount cannot exceed original amount."
            )

        expected_final = (
            original_amount
            - discount_amount
        )

        if final_amount != expected_final:
            raise ValidationError(
                "Final amount does not match the discount."
            )

        # ----------------------------------------------------
        # Prevent duplicate redemption for this order
        # ----------------------------------------------------

        existing = (
            CouponRedemption.objects
            .filter(
                coupon=locked_coupon,
                user=user,
                order=order,
            )
            .first()
        )

        if existing:
            raise CouponAlreadyRedeemedError(
                "This coupon has already been redeemed for this order."
            )

        # ----------------------------------------------------
        # Create immutable redemption record
        # ----------------------------------------------------

        try:
            redemption = CouponRedemption.objects.create(
                coupon=locked_coupon,
                user=user,
                order=order,
                original_amount=original_amount,
                discount_amount=discount_amount,
                final_amount=final_amount,
            )
        except IntegrityError:
            raise CouponAlreadyRedeemedError(
                "This coupon has already been redeemed for this order."
            )

        # ----------------------------------------------------
        # Increment aggregate usage
        # ----------------------------------------------------

        locked_coupon.used_count += 1

        locked_coupon.save(
            update_fields=[
                "used_count",
                "updated_at",
            ]
        )

        return redemption

    # ========================================================
    # REDEEM BY ORDER
    # ========================================================

    @classmethod
    @transaction.atomic
    def redeem_order_coupon(
        cls,
        order,
    ):
        """
        Redeem the coupon attached to a paid order.

        This is the preferred method for payment fulfillment.

        If the order has no coupon, returns None.
        """

        if not order.coupon_id:
            return None

        coupon = (
            Coupon.objects
            .get(pk=order.coupon_id)
        )

        original_amount = (
            order.original_amount
            if order.original_amount is not None
            else order.amount
        )

        discount_amount = (
            order.discount_amount
            or Decimal("0.00")
        )

        final_amount = order.amount

        return cls.redeem(
            coupon,
            user=order.user,
            order=order,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
        )