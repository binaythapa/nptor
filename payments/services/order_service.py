# payments/services/order_service.py

import secrets
import string
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from payments.models import PaymentOrder
from quiz.services.coupon_service import CouponService


class OrderService:
    """
    Central service for creating PaymentOrder records.

    PaymentOrder represents the commercial purchase.

    It does NOT grant access.

    Access is granted only after:

        Payment verification
            ↓
        PaymentFulfillmentService

    Coupon handling:

        1. Validate coupon
        2. Calculate discount
        3. Store coupon on PaymentOrder
        4. Store original amount
        5. Store discount amount
        6. Store final payable amount

    IMPORTANT:

        Coupon usage is NOT consumed when an order is created.

        Coupon redemption happens only after successful payment.
    """

    # =========================================================
    # ORDER NUMBER
    # =========================================================

    @staticmethod
    def generate_order_number():
        """
        Generate a unique human-readable order number.

        Example:

            ORD-Z2Q5QFC9UZ8M
        """

        alphabet = (
            string.ascii_uppercase
            + string.digits
        )

        while True:

            random_part = "".join(
                secrets.choice(alphabet)
                for _ in range(12)
            )

            order_number = (
                f"ORD-{random_part}"
            )

            if not PaymentOrder.objects.filter(
                order_number=order_number
            ).exists():

                return order_number

    # =========================================================
    # AMOUNT NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_amount(amount):
        """
        Convert the supplied amount into a valid Decimal.

        Returns:
            Decimal rounded to two decimal places.
        """

        try:

            amount = Decimal(
                str(amount)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):

            raise ValidationError(
                "Invalid payment amount."
            )

        if amount < Decimal("0.00"):

            raise ValidationError(
                "Payment amount cannot be negative."
            )

        return amount.quantize(
            Decimal("0.01")
        )

    # =========================================================
    # RESOURCE VALIDATION
    # =========================================================

    @staticmethod
    def _validate_resource(
        resource_type,
        resource,
    ):
        """
        Validate the resource type and return the resource
        fields required by PaymentOrder.
        """

        if not resource:

            raise ValidationError(
                "Purchase resource is required."
            )

        valid_resource_types = (
            PaymentOrder.RESOURCE_COURSE,
            PaymentOrder.RESOURCE_TRACK,
            PaymentOrder.RESOURCE_EXAM,
        )

        if resource_type not in valid_resource_types:

            raise ValidationError(
                "Invalid payment resource type."
            )

        resource_fields = {
            "course": None,
            "track": None,
            "exam": None,
        }

        if (
            resource_type
            == PaymentOrder.RESOURCE_COURSE
        ):

            resource_fields["course"] = resource

        elif (
            resource_type
            == PaymentOrder.RESOURCE_TRACK
        ):

            resource_fields["track"] = resource

        elif (
            resource_type
            == PaymentOrder.RESOURCE_EXAM
        ):

            resource_fields["exam"] = resource

        return resource_fields

    # =========================================================
    # CREATE ORDER
    # =========================================================

    @staticmethod
    @transaction.atomic
    def create_order(
        *,
        user,
        resource_type,
        resource,
        amount,
        currency="INR",
        coupon_code=None,
    ):
        """
        Create a PaymentOrder for:

            Course
            Track
            Exam

        Coupon support:

            coupon_code=None
                → normal order

            coupon_code="SAVE20"
                → validate and apply coupon

        Returns:
            PaymentOrder
        """

        # -----------------------------------------------------
        # USER VALIDATION
        # -----------------------------------------------------

        if not user:

            raise ValidationError(
                "User is required."
            )

        if not user.is_authenticated:

            raise ValidationError(
                "Authentication is required."
            )

        # -----------------------------------------------------
        # RESOURCE VALIDATION
        # -----------------------------------------------------

        resource_fields = (
            OrderService._validate_resource(
                resource_type,
                resource,
            )
        )

        # -----------------------------------------------------
        # ORIGINAL AMOUNT
        # -----------------------------------------------------

        original_amount = (
            OrderService._normalize_amount(
                amount
            )
        )

        # -----------------------------------------------------
        # COUPON
        # -----------------------------------------------------

        coupon = None

        discount_amount = Decimal(
            "0.00"
        )

        final_amount = original_amount

        if coupon_code:

            # -----------------------------------------------
            # Validate coupon against actual resource
            # -----------------------------------------------

            coupon_kwargs = {
                "course": None,
                "track": None,
                "exam": None,
            }

            if (
                resource_type
                == PaymentOrder.RESOURCE_COURSE
            ):

                coupon_kwargs["course"] = resource

            elif (
                resource_type
                == PaymentOrder.RESOURCE_TRACK
            ):

                coupon_kwargs["track"] = resource

            elif (
                resource_type
                == PaymentOrder.RESOURCE_EXAM
            ):

                coupon_kwargs["exam"] = resource

            coupon = (
                CouponService.validate_coupon(
                    coupon_code,
                    **coupon_kwargs,
                )
            )

            # -----------------------------------------------
            # Calculate discount
            # -----------------------------------------------

            pricing = (
                CouponService.calculate_price(
                    original_amount,
                    coupon,
                )
            )

            original_amount = pricing[
                "original_amount"
            ]

            discount_amount = pricing[
                "discount_amount"
            ]

            final_amount = pricing[
                "final_amount"
            ]

        # -----------------------------------------------------
        # CURRENCY
        # -----------------------------------------------------

        currency = (
            currency
            or "INR"
        ).strip().upper()

        if not currency:

            currency = "INR"

        # -----------------------------------------------------
        # GENERATE UNIQUE ORDER NUMBER
        # -----------------------------------------------------

        order_number = (
            OrderService.generate_order_number()
        )

        # -----------------------------------------------------
        # CREATE PAYMENT ORDER
        # -----------------------------------------------------

        order = PaymentOrder.objects.create(
            order_number=order_number,

            user=user,

            resource_type=resource_type,

            course=resource_fields["course"],

            track=resource_fields["track"],

            exam=resource_fields["exam"],

            # -----------------------------------------------
            # PRICING
            # -----------------------------------------------

            amount=final_amount,

            original_amount=original_amount,

            discount_amount=discount_amount,

            coupon=coupon,

            # -----------------------------------------------
            # PAYMENT
            # -----------------------------------------------

            currency=currency,

            status=PaymentOrder.STATUS_PENDING,
        )

        return order