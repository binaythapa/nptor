from datetime import timedelta
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from quiz.models import (
    ExamTrack,
    ExamTrackSubscription,
    Coupon
)
from quiz.services.access import can_access_exam


@login_required
@require_POST
def subscribe_track(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)
    user = request.user
    now = timezone.now()

    # -------------------------------
    # Prevent duplicate subscription
    # -------------------------------
    existing = ExamTrackSubscription.objects.filter(
        user=user,
        track=track,
        is_active=True
    ).first()

    if existing:
        messages.info(request, "You already have an active subscription.")
        return redirect("quiz:student_dashboard")

    # -------------------------------
    # Coupon handling
    # -------------------------------
    coupon_code = request.POST.get("coupon", "").strip()
    coupon = None

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if not coupon or not coupon.is_valid():
            messages.error(request, "Invalid or expired coupon.")
            return redirect("quiz:exam_list")

        # coupon scope check
        if coupon.track and coupon.track != track:
            messages.error(request, "Coupon not valid for this track.")
            return redirect("quiz:exam_list")

    # -------------------------------
    # Trial logic
    # -------------------------------
    trial_days = track.trial_days
    if coupon and coupon.extra_trial_days:
        trial_days += coupon.extra_trial_days

    # -------------------------------
    # Expiry logic
    # -------------------------------
    if track.pricing_type == track.PRICING_MONTHLY:
        expires_at = now + timedelta(days=30)
    elif track.pricing_type == track.PRICING_FREE:
        expires_at = now + timedelta(days=trial_days)
    else:  # lifetime
        expires_at = None

    # -------------------------------
    # Create subscription
    # -------------------------------
    ExamTrackSubscription.objects.create(
        user=user,
        track=track,
        is_active=True,
        expires_at=expires_at,
        payment_required=(track.pricing_type != track.PRICING_FREE),
        amount=track.monthly_price if track.pricing_type == track.PRICING_MONTHLY else track.lifetime_price,
        currency=track.currency,
    )

    if coupon:
        coupon.mark_used()

    messages.success(request, "Subscription activated successfully 🎉")
    return redirect("quiz:student_dashboard")
