from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from quiz.models import (
    PaymentRecord,
    Exam,
    ExamTrack,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
)


class PaymentService:
    """
    Single source of truth for payments & access
    """

    # =====================================================
    # LOW LEVEL – DB ONLY
    # =====================================================
    @staticmethod
    def record_payment(
        user,
        amount,
        *,
        exam=None,
        track=None,
        method="manual",
        reference_id=None,
        created_by_admin=False,
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

    # =====================================================
    # HIGH LEVEL – PAYMENT + SUBSCRIPTION
    # =====================================================
    @staticmethod
    @transaction.atomic
    def apply_manual_payment(
        *,
        user,
        exam: Exam = None,
        track: ExamTrack = None,
        coupon: Coupon = None,
        reference_id="",
    ):
        """
        Admin-only payment handler
        """

        # ---------------- VALIDATION ----------------
        if not exam and not track:
            raise ValueError("Exam or Track required")

        if exam and track:
            raise ValueError("Cannot pay for both exam and track")

        # ---------------- BASE AMOUNT ----------------
        if exam:
            base_amount = Decimal("0") if exam.is_free else Decimal(exam.price or 0)
        else:
            if track.pricing_type == track.PRICING_FREE:
                base_amount = Decimal("0")
            elif track.pricing_type == track.PRICING_MONTHLY:
                base_amount = Decimal(track.monthly_price)
            else:
                base_amount = Decimal(track.lifetime_price)

        final_amount = base_amount
        extra_trial_days = 0

        # ---------------- COUPON ----------------
        if coupon:
            if not coupon.is_valid():
                raise ValueError("Invalid coupon")

            if coupon.percent_off:
                final_amount -= (final_amount * Decimal(coupon.percent_off) / 100)

            if coupon.flat_off:
                final_amount -= Decimal(coupon.flat_off)

            final_amount = max(final_amount, Decimal("0"))
            extra_trial_days = coupon.extra_trial_days or 0
            coupon.mark_used()

        # ---------------- PAYMENT RECORD ----------------
        payment = PaymentService.record_payment(
            user=user,
            exam=exam,
            track=track,
            amount=final_amount,
            method="manual",
            reference_id=reference_id,
            created_by_admin=True,
        )

        # ---------------- SUBSCRIPTION ----------------
        expires_at = None

        if track and track.pricing_type == track.PRICING_MONTHLY:
            expires_at = timezone.now() + timezone.timedelta(
                days=30 + extra_trial_days
            )

        if track:
            ExamTrackSubscription.objects.update_or_create(
                user=user,
                track=track,
                defaults={
                    "is_active": True,
                    "expires_at": expires_at,
                    "payment_required": final_amount > 0,
                    "amount": final_amount,
                    "currency": "INR",
                    "subscribed_by_admin": True,
                },
            )

        if exam:
            ExamSubscription.objects.update_or_create(
                user=user,
                exam=exam,
                defaults={
                    "is_active": True,
                    "expires_at": expires_at,
                    "payment_required": final_amount > 0,
                    "amount": final_amount,
                    "currency": "INR",
                    "subscribed_by_admin": True,
                },
            )

        return payment
