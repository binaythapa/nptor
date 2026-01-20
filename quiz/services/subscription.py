from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription

def has_valid_subscription(user, exam):
    track = exam.track

    # Track-level subscription
    if track and track.subscription_scope == "track":
        sub = ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True
        ).first()
        return sub and sub.is_valid()

    # Exam-level subscription
    sub = ExamSubscription.objects.filter(
        user=user,
        exam=exam,
        is_active=True
    ).first()
    return sub and sub.is_valid()



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from quiz.models import Exam
from quiz.services.coupon_service import CouponService
from quiz.services.pricing_service import PricingService
from quiz.services.subscription_service import SubscriptionService
from quiz.services.payment_service import PaymentService


@login_required
def subscribe_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    coupon_code = request.POST.get("coupon")
    coupon = None

    if coupon_code:
        coupon, error = CouponService.validate_coupon(
            coupon_code,
            exam=exam
        )
        if error:
            messages.error(request, error)
            return redirect("quiz:exam_list")

    base_price = exam.price or 0
    final_price = PricingService.calculate_price(base_price, coupon)

    # 🔹 Determine expiry
    expires_at = None
    if coupon and coupon.extra_trial_days:
        expires_at = timezone.now() + timezone.timedelta(
            days=coupon.extra_trial_days
        )

    # 🔹 If payment required
    if final_price > 0:
        # ⛔ Integrate Razorpay / Stripe here
        payment_reference = "SIMULATED_PAYMENT_ID"

        PaymentService.record_payment(
            user=request.user,
            exam=exam,
            amount=final_price,
            reference_id=payment_reference
        )

    # 🔹 Grant subscription
    SubscriptionService.create_exam_subscription(
        user=request.user,
        exam=exam,
        expires_at=expires_at,
        payment_required=final_price > 0
    )

    if coupon:
        coupon.mark_used()

    messages.success(request, "Subscription activated!")
    return redirect("quiz:dashboard")

