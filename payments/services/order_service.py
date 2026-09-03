import secrets
import string
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from payments.models import PaymentOrder
from quiz.services.coupon_service import CouponService
from subscriptions.services.plan_service import (
    get_plan_for_course,
    get_plan_for_track,
)


class OrderService:
    """Create immutable payment-order pricing from server-side resource data."""

    @staticmethod
    def generate_order_number():
        alphabet = string.ascii_uppercase + string.digits
        while True:
            random_part = "".join(secrets.choice(alphabet) for _ in range(12))
            order_number = f"ORD-{random_part}"
            if not PaymentOrder.objects.filter(order_number=order_number).exists():
                return order_number

    @staticmethod
    def _normalize_amount(amount):
        try:
            value = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Invalid payment amount.")
        if value < Decimal("0.00"):
            raise ValidationError("Payment amount cannot be negative.")
        return value.quantize(Decimal("0.01"))

    @staticmethod
    def _validate_resource(resource_type, resource):
        if not resource:
            raise ValidationError("Purchase resource is required.")
        valid = (
            PaymentOrder.RESOURCE_COURSE,
            PaymentOrder.RESOURCE_TRACK,
            PaymentOrder.RESOURCE_EXAM,
        )
        if resource_type not in valid:
            raise ValidationError("Invalid payment resource type.")
        return {
            "course": resource if resource_type == PaymentOrder.RESOURCE_COURSE else None,
            "track": resource if resource_type == PaymentOrder.RESOURCE_TRACK else None,
            "exam": resource if resource_type == PaymentOrder.RESOURCE_EXAM else None,
        }

    @staticmethod
    def _authoritative_pricing(resource_type, resource):
        if resource_type == PaymentOrder.RESOURCE_COURSE:
            plan = get_plan_for_course(resource)
        elif resource_type == PaymentOrder.RESOURCE_TRACK:
            plan = get_plan_for_track(resource)
        else:
            # Individual exams already expose their commercial price.
            plan = None

        if resource_type in (
            PaymentOrder.RESOURCE_COURSE,
            PaymentOrder.RESOURCE_TRACK,
        ):
            if not plan:
                raise ValidationError(
                    "No active subscription plan is configured for this resource."
                )
            return plan.price, (plan.currency or "INR").strip().upper()

        return resource.price, (
            getattr(resource, "currency", None) or "INR"
        ).strip().upper()

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
        if not user or not user.is_authenticated:
            raise ValidationError("Authentication is required.")

        resource_fields = OrderService._validate_resource(resource_type, resource)
        authoritative_amount, authoritative_currency = (
            OrderService._authoritative_pricing(resource_type, resource)
        )
        supplied_amount = OrderService._normalize_amount(amount)
        expected_amount = OrderService._normalize_amount(authoritative_amount)
        supplied_currency = (currency or "INR").strip().upper()

        if supplied_amount != expected_amount:
            raise ValidationError("Payment amount does not match the current price.")
        if supplied_currency != authoritative_currency:
            raise ValidationError("Payment currency does not match the current price.")

        original_amount = expected_amount
        discount_amount = Decimal("0.00")
        final_amount = original_amount
        coupon = None

        if coupon_code:
            coupon_kwargs = {
                "course": resource if resource_type == PaymentOrder.RESOURCE_COURSE else None,
                "track": resource if resource_type == PaymentOrder.RESOURCE_TRACK else None,
                "exam": resource if resource_type == PaymentOrder.RESOURCE_EXAM else None,
            }
            coupon = CouponService.validate_coupon(coupon_code, **coupon_kwargs)
            pricing = CouponService.calculate_price(original_amount, coupon)
            original_amount = pricing["original_amount"]
            discount_amount = pricing["discount_amount"]
            final_amount = pricing["final_amount"]

        return PaymentOrder.objects.create(
            order_number=OrderService.generate_order_number(),
            user=user,
            resource_type=resource_type,
            course=resource_fields["course"],
            track=resource_fields["track"],
            exam=resource_fields["exam"],
            amount=final_amount,
            original_amount=original_amount,
            discount_amount=discount_amount,
            coupon=coupon,
            currency=authoritative_currency,
            status=PaymentOrder.STATUS_PENDING,
        )
