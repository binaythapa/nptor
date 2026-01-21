from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from quiz.models import Exam, ExamTrack, Coupon
from quiz.services.subscription_service import SubscriptionService
from quiz.models import PaymentRecord


class PaymentService:
    """
    Handles ONLY payment logic.
    Does NOT directly manage subscriptions.
    """

    # -------------------------------------------
    # LOW LEVEL: record payment row
    # -------------------------------------------
    @staticmethod
    def record_payment(
        *,
        user,
        amount,
        exam=None,
        track=None,
        method="manual",
        reference_id="",
        created_by_admin=True,
    ):
        return PaymentRecord.objects.create(
            user=user,
            exam=exam,
            track=track,
            amount=amount,
            currency="INR",
            payment_method=method,
            reference_id=reference_id,
            created_by_admin=created_by_admin,
        )

    # -------------------------------------------
    # HIGH LEVEL: admin manual payment
    # -------------------------------------------
    @staticmethod
    @transaction.atomic
    def apply_manual_payment(
        *,
        user,
        exam: Exam = None,
        track: ExamTrack = None,
        coupon: Coupon = None,
        reference_id: str = "",
    ):
        """
        Admin manual payment flow:

        1️⃣ Validate input
        2️⃣ Calculate base price
        3️⃣ Apply coupon
        4️⃣ Record payment (even ₹0)
        5️⃣ Grant subscription via SubscriptionService
        """

        # -------------------------------------------------
        # 1️⃣ VALIDATION
        # -------------------------------------------------
        if not exam and not track:
            raise ValueError("Either exam or track is required")

        if exam and track:
            raise ValueError("Only one of exam or track is allowed")

        # -------------------------------------------------
        # 2️⃣ BASE PRICE
        # -------------------------------------------------
        if exam:
            base_amount = Decimal("0") if exam.is_free else Decimal(exam.price or 0)
        else:
            if track.pricing_type == track.PRICING_FREE:
                base_amount = Decimal("0")
            elif track.pricing_type == track.PRICING_MONTHLY:
                base_amount = Decimal(track.monthly_price or 0)
            else:
                base_amount = Decimal(track.lifetime_price or 0)

        final_amount = base_amount
        extra_trial_days = 0

        # -------------------------------------------------
        # 3️⃣ APPLY COUPON
        # -------------------------------------------------
        if coupon:
            if not coupon.is_valid():
                raise ValueError("Invalid or expired coupon")

            if coupon.percent_off:
                final_amount -= (final_amount * Decimal(coupon.percent_off) / 100)

            if coupon.flat_off:
                final_amount -= Decimal(coupon.flat_off)

            final_amount = max(final_amount, Decimal("0"))
            extra_trial_days = coupon.extra_trial_days or 0
            coupon.mark_used()

        # -------------------------------------------------
        # 4️⃣ RECORD PAYMENT (₹0 INCLUDED)
        # -------------------------------------------------
        payment = PaymentService.record_payment(
            user=user,
            exam=exam,
            track=track,
            amount=final_amount,
            method="manual",
            reference_id=reference_id,
            created_by_admin=True,
        )

        # -------------------------------------------------
        # 5️⃣ GRANT SUBSCRIPTION (delegate)
        # -------------------------------------------------
        expires_at = None

        if track and track.pricing_type == track.PRICING_MONTHLY:
            expires_at = timezone.now() + timezone.timedelta(
                days=30 + extra_trial_days
            )

        SubscriptionService.subscribe(
            user=user,
            exam=exam,
            track=track,
            amount=final_amount,
            payment_required=final_amount > 0,
            expires_at=expires_at,
            subscribed_by_admin=True,
        )

        return payment
