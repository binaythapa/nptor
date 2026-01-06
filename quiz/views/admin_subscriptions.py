import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from quiz.models import (
    Exam,
    ExamTrack,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
)

logger = logging.getLogger(__name__)
User = get_user_model()


# =====================================================
# ADMIN SUBSCRIPTION PANEL
# =====================================================
@staff_member_required
def subscription_admin_panel(request):
    context = {
        # Tracks & Exams
        "tracks": ExamTrack.objects.all().order_by("-created_at"),
        "exams": Exam.objects.select_related("track").all(),
        "users": User.objects.filter(is_active=True),

        # Subscriptions
        "track_subs": (
            ExamTrackSubscription.objects
            .select_related("user", "track")
            .order_by("-subscribed_at")
        ),
        "exam_subs": (
            ExamSubscription.objects
            .select_related("user", "exam")
            .order_by("-subscribed_at")
        ),

        # Coupons
        "coupons": Coupon.objects.all().order_by("-valid_to"),

        "now": timezone.now(),
    }

    return render(request, "quiz/admin_subscription_panel.html", context)


# =====================================================
# ADMIN: SUBSCRIBE / REVOKE TRACK
# =====================================================
@staff_member_required
@require_POST
def admin_subscribe_track(request):
    user_id = request.POST.get("user_id")
    track_id = request.POST.get("track_id")

    track = get_object_or_404(ExamTrack, id=track_id)

    ExamTrackSubscription.objects.update_or_create(
        user_id=user_id,
        track=track,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "expires_at": None,
            "subscribed_by_admin": True,
        }
    )

    return JsonResponse({"success": True})


@staff_member_required
@require_POST
def admin_revoke_track(request):
    ExamTrackSubscription.objects.filter(
        user_id=request.POST.get("user_id"),
        track_id=request.POST.get("track_id"),
    ).update(is_active=False)

    return JsonResponse({"success": True})


# =====================================================
# ADMIN: SUBSCRIBE / REVOKE EXAM
# =====================================================
@staff_member_required
@require_POST
def admin_subscribe_exam(request):
    user_id = request.POST.get("user_id")
    exam_id = request.POST.get("exam_id")

    exam = get_object_or_404(Exam, id=exam_id)

    ExamSubscription.objects.update_or_create(
        user_id=user_id,
        exam=exam,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "currency": "INR",
            "expires_at": None,
            "subscribed_by_admin": True,
        }
    )

    return JsonResponse({"success": True})


@staff_member_required
@require_POST
def admin_revoke_exam(request):
    ExamSubscription.objects.filter(
        user_id=request.POST.get("user_id"),
        exam_id=request.POST.get("exam_id"),
    ).update(is_active=False)

    return JsonResponse({"success": True})


# =====================================================
# TOGGLE TRACK ACTIVE
# =====================================================
@staff_member_required
@require_POST
def toggle_track_status(request):
    track_id = request.POST.get("track_id")

    try:
        track = ExamTrack.objects.get(id=track_id)
        track.is_active = not track.is_active
        track.save()
        return JsonResponse({"success": True, "new_status": track.is_active})
    except ExamTrack.DoesNotExist:
        return JsonResponse({"success": False})


# =====================================================
# TOGGLE COUPON ACTIVE
# =====================================================
@staff_member_required
@require_POST
def toggle_coupon_status(request):
    coupon_id = request.POST.get("coupon_id")

    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save()
        return JsonResponse({"success": True, "new_status": coupon.is_active})
    except Coupon.DoesNotExist:
        return JsonResponse({"success": False})


# =====================================================
# CREATE COUPON (MODAL)
# =====================================================
@staff_member_required
@require_POST
def create_coupon_ajax(request):
    code = request.POST.get("code").upper()
    percent_off = request.POST.get("percent_off") or None
    flat_off = request.POST.get("flat_off") or None
    valid_days = int(request.POST.get("valid_days", 7))

    if Coupon.objects.filter(code=code).exists():
        return JsonResponse({"success": False, "error": "Coupon already exists"})

    Coupon.objects.create(
        code=code,
        percent_off=int(percent_off) if percent_off else None,
        flat_off=Decimal(flat_off) if flat_off else None,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=valid_days),
        is_active=True,
    )

    return JsonResponse({"success": True})


# =====================================================
# UPDATE TRACK PRICING TYPE (SINGLE SOURCE OF TRUTH)
# =====================================================
@staff_member_required
@require_POST
def update_track_pricing_type(request):
    track_id = request.POST.get("track_id")
    pricing_type = request.POST.get("pricing_type")
    monthly_price = request.POST.get("monthly_price") or None
    lifetime_price = request.POST.get("lifetime_price") or None

    try:
        track = ExamTrack.objects.get(id=track_id)
        track.pricing_type = pricing_type

        if pricing_type == "free":
            track.monthly_price = None
            track.lifetime_price = None

        elif pricing_type == "monthly":
            if not monthly_price:
                return JsonResponse({"success": False, "error": "Monthly price required"})
            track.monthly_price = monthly_price
            track.lifetime_price = None

        elif pricing_type == "lifetime":
            if not lifetime_price:
                return JsonResponse({"success": False, "error": "Lifetime price required"})
            track.lifetime_price = lifetime_price
            track.monthly_price = None

        track.save()
        return JsonResponse({"success": True})

    except ExamTrack.DoesNotExist:
        return JsonResponse({"success": False, "error": "Track not found"})


# =====================================================
# ADMIN: UPDATE SUBSCRIPTION EXPIRY (INLINE EDIT)
# =====================================================
@staff_member_required
@require_POST
def admin_update_exam_expiry(request):
    user_id = request.POST.get("user_id")
    exam_id = request.POST.get("exam_id")
    expires_at = request.POST.get("expires_at")

    qs = ExamSubscription.objects.filter(user_id=user_id, exam_id=exam_id)

    if not qs.exists():
        return JsonResponse({"success": False, "error": "Subscription not found"})

    if expires_at:
        qs.update(expires_at=expires_at, is_active=True)
    else:
        qs.update(expires_at=None, is_active=True)

    return JsonResponse({"success": True})


@staff_member_required
@require_POST
def admin_update_track_expiry(request):
    user_id = request.POST.get("user_id")
    track_id = request.POST.get("track_id")
    expires_at = request.POST.get("expires_at")

    qs = ExamTrackSubscription.objects.filter(user_id=user_id, track_id=track_id)

    if not qs.exists():
        return JsonResponse({"success": False, "error": "Subscription not found"})

    if expires_at:
        qs.update(expires_at=expires_at, is_active=True)
    else:
        qs.update(expires_at=None, is_active=True)

    return JsonResponse({"success": True})

@staff_member_required
@require_POST
def admin_add_exam_days(request):
    sub = ExamSubscription.objects.get(
        user_id=request.POST["user_id"],
        exam_id=request.POST["item_id"]
    )
    sub.expires_at = (sub.expires_at or timezone.now()) + timedelta(days=int(request.POST["days"]))
    sub.save()
    return JsonResponse({"success": True})


@staff_member_required
@require_POST
def admin_add_track_days(request):
    sub = ExamTrackSubscription.objects.get(
        user_id=request.POST["user_id"],
        track_id=request.POST["item_id"]
    )
    sub.expires_at = (sub.expires_at or timezone.now()) + timedelta(days=int(request.POST["days"]))
    sub.save()
    return JsonResponse({"success": True})
