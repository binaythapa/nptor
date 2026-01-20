from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from quiz.models import (
    Exam,
    ExamTrack,
    ExamSubscription,
    ExamTrackSubscription,
)
from quiz.services.payment_service import PaymentService


from quiz.services.subscription_guard import has_active_track_subscription

@login_required
@require_POST
def subscribe_track(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    # 🔐 GUARD: already subscribed
    existing = ExamTrackSubscription.objects.filter(
        user=request.user,
        track=track,
        is_active=True
    ).first()

    if existing and existing.is_valid():
        messages.info(request, "You are already subscribed to this track.")
        return redirect("quiz:exam_list")

    # FREE ONLY — paid handled by admin / contact flow
    if track.pricing_type != ExamTrack.PRICING_FREE:
        messages.error(request, "Paid tracks require admin approval.")
        return redirect("quiz:exam_list")

    ExamTrackSubscription.objects.update_or_create(
        user=request.user,
        track=track,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "expires_at": None,
            "subscribed_by_admin": False,
        }
    )

    messages.success(request, "Track subscribed successfully.")
    return redirect("quiz:student_dashboard")





from quiz.services.subscription_guard import has_active_exam_subscription

@login_required
@require_POST
def subscribe_exam(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_published=True
    )

    # 🔐 GUARD: already subscribed
    existing = ExamSubscription.objects.filter(
        user=request.user,
        exam=exam,
        is_active=True
    ).first()

    if existing and existing.is_valid():
        messages.info(request, "You are already subscribed to this exam.")
        return redirect("quiz:exam_list")

    if not exam.is_free:
        messages.error(request, "Paid exams require admin approval.")
        return redirect("quiz:exam_list")

    ExamSubscription.objects.update_or_create(
        user=request.user,
        exam=exam,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "currency": "INR",
            "expires_at": None,
            "subscribed_by_admin": False,
        }
    )

    messages.success(request, "Exam subscribed successfully.")
    return redirect("quiz:exam_list")





@login_required
def subscribe_track_checkout(request, track_id):
    """
    Show checkout for PAID track
    """

    track = get_object_or_404(
        ExamTrack,
        id=track_id,
        is_active=True
    )

    if track.pricing_type == ExamTrack.PRICING_FREE:
        return redirect("quiz:subscribe_track", track_id=track.id)

    return render(request, "quiz/checkout.html", {
        "track": track,
    })



@login_required
@require_POST
def finalize_track_subscription(request, track_id):
    """
    Final step after checkout
    Applies coupon, records payment, grants access
    """

    track = get_object_or_404(
        ExamTrack,
        id=track_id,
        is_active=True
    )

    coupon_code = request.POST.get("coupon", "").strip().upper()

    try:
        PaymentService.apply_manual_payment(
            user=request.user,
            track=track,
            coupon=coupon_code and None,  # real coupon object resolved in service
            reference_id="USER_CHECKOUT",
        )
    except Exception as e:
        messages.error(request, str(e))
        return redirect("quiz:subscribe_track_checkout", track_id=track.id)

    messages.success(request, "Subscription activated successfully.")
    return redirect("quiz:student_dashboard")



@login_required
@require_POST
def log_enrollment_lead(request):
    """
    Logs interest for paid items
    """

    item_type = request.POST.get("type")   # exam / track
    item_id = request.POST.get("item_id")

    if item_type not in ("exam", "track"):
        return JsonResponse({"ok": False}, status=400)

    return JsonResponse({"ok": True})


@login_required
def subscribe_track_checkout(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    if has_active_track_subscription(request.user, track):
        messages.info(request, "You already have access to this track.")
        return redirect("quiz:student_dashboard")

    return render(request, "quiz/checkout.html", {
        "track": track,
    })
