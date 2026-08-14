# quiz/views/admin_subscriptions.py

import logging
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from quiz.models import (
    Exam,
    ExamTrack,
    ExamSubscription,
    ExamTrackSubscription,
    SubscriptionPlan,
    Coupon,
    PaymentRecord,
)

from quiz.services.payment_service import PaymentService
from quiz.services.subscription_service import SubscriptionService


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# ADMIN SUBSCRIPTION PANEL
# ============================================================

@staff_member_required
def subscription_admin_panel(request):
    """
    Main administration dashboard for subscriptions.
    """

    context = {
        # ----------------------------------------------------
        # TRACKS & EXAMS
        # ----------------------------------------------------

        "tracks": (
            ExamTrack.objects
            .all()
            .order_by("-created_at")
        ),

        "exams": (
            Exam.objects
            .select_related("track")
            .all()
        ),

        "users": (
            User.objects
            .filter(is_active=True)
            .order_by("username")
        ),

        # ----------------------------------------------------
        # TRACK SUBSCRIPTIONS
        # ----------------------------------------------------

        "track_subs": (
            ExamTrackSubscription.objects
            .select_related(
                "user",
                "track",
            )
            .order_by("-subscribed_at")
        ),

        # ----------------------------------------------------
        # EXAM SUBSCRIPTIONS
        # ----------------------------------------------------

        "exam_subs": (
            ExamSubscription.objects
            .select_related(
                "user",
                "exam",
            )
            .order_by("-subscribed_at")
        ),

        # ----------------------------------------------------
        # COUPONS
        # ----------------------------------------------------

        "coupons": (
            Coupon.objects
            .all()
            .order_by("-valid_to")
        ),

        # ----------------------------------------------------
        # CURRENT TIME
        # ----------------------------------------------------

        "now": timezone.now(),
    }

    return render(
        request,
        "quiz/student/subscription/dashboard.html",
        context,
    )


# ============================================================
# ADMIN: SUBSCRIBE TO TRACK
# ============================================================

@staff_member_required
@require_POST
def admin_subscribe_track(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    track = get_object_or_404(
        ExamTrack,
        id=request.POST.get("track_id"),
    )

    SubscriptionService.subscribe(
        user=user,
        track=track,
        amount=0,
        payment_required=False,
        subscribed_by_admin=True,
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# ADMIN: REVOKE TRACK SUBSCRIPTION
# ============================================================

@staff_member_required
@require_POST
def admin_revoke_track(request):

    ExamTrackSubscription.objects.filter(
        user_id=request.POST.get("user_id"),
        track_id=request.POST.get("track_id"),
    ).update(
        is_active=False
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# ADMIN: SUBSCRIBE TO EXAM
# ============================================================

@staff_member_required
@require_POST
def admin_subscribe_exam(request):

    user = get_object_or_404(
        User,
        id=request.POST.get("user_id"),
    )

    exam = get_object_or_404(
        Exam,
        id=request.POST.get("exam_id"),
    )

    SubscriptionService.subscribe(
        user=user,
        exam=exam,
        amount=0,
        payment_required=False,
        subscribed_by_admin=True,
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# ADMIN: REVOKE EXAM SUBSCRIPTION
# ============================================================

@staff_member_required
@require_POST
def admin_revoke_exam(request):

    ExamSubscription.objects.filter(
        user_id=request.POST.get("user_id"),
        exam_id=request.POST.get("exam_id"),
    ).update(
        is_active=False
    )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# TOGGLE TRACK ACTIVE STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_track_status(request):

    track_id = request.POST.get(
        "track_id"
    )

    try:

        track = ExamTrack.objects.get(
            id=track_id
        )

        track.is_active = not track.is_active

        track.save(
            update_fields=[
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "new_status": track.is_active,
            }
        )

    except ExamTrack.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Track not found",
            },
            status=404,
        )


# ============================================================
# TOGGLE COUPON ACTIVE STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_coupon_status(request):

    coupon_id = request.POST.get(
        "coupon_id"
    )

    try:

        coupon = Coupon.objects.get(
            id=coupon_id
        )

        coupon.is_active = not coupon.is_active

        coupon.save(
            update_fields=[
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "new_status": coupon.is_active,
            }
        )

    except Coupon.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon not found",
            },
            status=404,
        )


# ============================================================
# CREATE COUPON
# ============================================================

@staff_member_required
@require_POST
def create_coupon_ajax(request):

    code = (
        request.POST.get("code") or ""
    ).strip().upper()

    percent_off = (
        request.POST.get("percent_off")
        or None
    )

    flat_off = (
        request.POST.get("flat_off")
        or None
    )

    try:
        valid_days = int(
            request.POST.get(
                "valid_days",
                7,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        valid_days = 7

    if not code:

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon code is required",
            },
            status=400,
        )

    if Coupon.objects.filter(
        code=code
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": "Coupon already exists",
            }
        )

    try:

        Coupon.objects.create(
            code=code,

            percent_off=(
                int(percent_off)
                if percent_off
                else None
            ),

            flat_off=(
                Decimal(flat_off)
                if flat_off
                else None
            ),

            valid_from=timezone.now(),

            valid_to=(
                timezone.now()
                + timedelta(
                    days=valid_days
                )
            ),

            is_active=True,
        )

    except Exception as exc:

        logger.exception(
            "Failed to create coupon"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# UPDATE TRACK PRICING TYPE
# ============================================================

@staff_member_required
@require_POST
def update_track_pricing_type(request):

    track_id = request.POST.get(
        "track_id"
    )

    pricing_type = request.POST.get(
        "pricing_type"
    )

    monthly_price = (
        request.POST.get(
            "monthly_price"
        )
        or None
    )

    lifetime_price = (
        request.POST.get(
            "lifetime_price"
        )
        or None
    )

    try:

        track = ExamTrack.objects.get(
            id=track_id
        )

        track.pricing_type = pricing_type

        # ----------------------------------------------------
        # FREE
        # ----------------------------------------------------

        if pricing_type == "free":

            track.monthly_price = None
            track.lifetime_price = None

        # ----------------------------------------------------
        # MONTHLY
        # ----------------------------------------------------

        elif pricing_type == "monthly":

            if not monthly_price:

                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Monthly price required"
                        ),
                    }
                )

            track.monthly_price = monthly_price
            track.lifetime_price = None

        # ----------------------------------------------------
        # LIFETIME
        # ----------------------------------------------------

        elif pricing_type == "lifetime":

            if not lifetime_price:

                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Lifetime price required"
                        ),
                    }
                )

            track.lifetime_price = lifetime_price
            track.monthly_price = None

        else:

            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid pricing type",
                },
                status=400,
            )

        track.save()

        return JsonResponse(
            {
                "success": True,
            }
        )

    except ExamTrack.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Track not found",
            },
            status=404,
        )


# ============================================================
# UPDATE EXAM SUBSCRIPTION EXPIRY
# ============================================================

@staff_member_required
@require_POST
def admin_update_exam_expiry(request):

    user_id = request.POST.get(
        "user_id"
    )

    exam_id = request.POST.get(
        "exam_id"
    )

    expires_at = request.POST.get(
        "expires_at"
    )

    qs = ExamSubscription.objects.filter(
        user_id=user_id,
        exam_id=exam_id,
    )

    if not qs.exists():

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    if expires_at:

        qs.update(
            expires_at=expires_at,
            is_active=True,
        )

    else:

        qs.update(
            expires_at=None,
            is_active=True,
        )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# UPDATE TRACK SUBSCRIPTION EXPIRY
# ============================================================

@staff_member_required
@require_POST
def admin_update_track_expiry(request):

    user_id = request.POST.get(
        "user_id"
    )

    track_id = request.POST.get(
        "track_id"
    )

    expires_at = request.POST.get(
        "expires_at"
    )

    qs = ExamTrackSubscription.objects.filter(
        user_id=user_id,
        track_id=track_id,
    )

    if not qs.exists():

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    if expires_at:

        qs.update(
            expires_at=expires_at,
            is_active=True,
        )

    else:

        qs.update(
            expires_at=None,
            is_active=True,
        )

    return JsonResponse(
        {
            "success": True,
        }
    )


# ============================================================
# ADD EXAM SUBSCRIPTION DAYS
# ============================================================

@staff_member_required
@require_POST
def admin_add_exam_days(request):

    try:

        sub = ExamSubscription.objects.get(
            user_id=request.POST["user_id"],
            exam_id=request.POST["item_id"],
        )

        days = int(
            request.POST["days"]
        )

        sub.expires_at = (
            sub.expires_at
            or timezone.now()
        ) + timedelta(
            days=days
        )

        sub.is_active = True

        sub.save(
            update_fields=[
                "expires_at",
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
            }
        )

    except ExamSubscription.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid number of days",
            },
            status=400,
        )


# ============================================================
# ADD TRACK SUBSCRIPTION DAYS
# ============================================================

@staff_member_required
@require_POST
def admin_add_track_days(request):

    try:

        sub = ExamTrackSubscription.objects.get(
            user_id=request.POST["user_id"],
            track_id=request.POST["item_id"],
        )

        days = int(
            request.POST["days"]
        )

        sub.expires_at = (
            sub.expires_at
            or timezone.now()
        ) + timedelta(
            days=days
        )

        sub.is_active = True

        sub.save(
            update_fields=[
                "expires_at",
                "is_active",
            ]
        )

        return JsonResponse(
            {
                "success": True,
            }
        )

    except ExamTrackSubscription.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Subscription not found",
            },
            status=404,
        )

    except (
        TypeError,
        ValueError,
    ):

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid number of days",
            },
            status=400,
        )


# ============================================================
# FORMS
# ============================================================

class ExamForm(forms.ModelForm):

    class Meta:

        model = Exam

        fields = [
            "title",
            "track",
            "question_count",
            "duration_seconds",
            "passing_score",
            "is_free",
            "price",
            "currency",
            "is_published",
            "max_mock_attempts",
        ]


class TrackForm(forms.ModelForm):

    class Meta:

        model = ExamTrack

        fields = "__all__"

    def clean(self):

        cleaned = super().clean()

        plans = cleaned.get(
            "subscription_plans"
        )

        pricing_type = cleaned.get(
            "pricing_type"
        )

        if (
            plans
            and pricing_type
            != ExamTrack.PRICING_FREE
        ):

            raise forms.ValidationError(
                "Do not use legacy pricing when "
                "subscription plans are selected."
            )

        return cleaned


class CouponForm(forms.ModelForm):

    class Meta:

        model = Coupon

        fields = [
            "code",
            "percent_off",
            "flat_off",
            "track",
            "exam",
            "valid_from",
            "valid_to",
            "usage_limit",
            "extra_trial_days",
            "is_active",
        ]

        widgets = {

            "valid_from": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local"
                }
            ),

            "valid_to": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local"
                }
            ),
        }


# ============================================================
# EXAMS
# ============================================================

@staff_member_required
def admin_exam_list(request):

    exams = (
        Exam.objects
        .select_related("track")
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/exam_list.html",
        {
            "exams": exams,
        },
    )


@staff_member_required
def admin_exam_create(request):

    form = ExamForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_exam_list"
        )

    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@staff_member_required
def admin_exam_update(
    request,
    pk,
):

    exam = get_object_or_404(
        Exam,
        pk=pk,
    )

    form = ExamForm(
        request.POST or None,
        instance=exam,
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_exam_list"
        )

    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {
            "form": form,
            "mode": "edit",
        },
    )


@staff_member_required
def admin_exam_delete(
    request,
    pk,
):

    exam = get_object_or_404(
        Exam,
        pk=pk,
    )

    exam.delete()

    return redirect(
        "quiz:admin_exam_list"
    )


# ============================================================
# TRACKS
# ============================================================

@staff_member_required
def admin_track_list(request):

    tracks = (
        ExamTrack.objects
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/track_list.html",
        {
            "tracks": tracks,
        },
    )


@staff_member_required
def admin_track_create(request):

    form = TrackForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_track_list"
        )

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {
            "form": form,
            "mode": "create",
        },
    )


@staff_member_required
def admin_track_update(
    request,
    pk,
):

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
    )

    form = TrackForm(
        request.POST or None,
        instance=track,
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_track_list"
        )

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {
            "form": form,
            "mode": "edit",
        },
    )


@staff_member_required
def admin_track_delete(
    request,
    pk,
):

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
    )

    track.delete()

    return redirect(
        "quiz:admin_track_list"
    )


# ============================================================
# COUPONS
# ============================================================

@staff_member_required
def admin_coupon_list(request):

    coupons = (
        Coupon.objects
        .order_by("-created_at")
    )

    return render(
        request,
        "quiz/student/subscription/coupon_list.html",
        {
            "coupons": coupons,
        },
    )


@staff_member_required
def admin_coupon_create(request):

    form = CouponForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "quiz:admin_coupon_list"
        )

    return render(
        request,
        "quiz/student/subscription/coupon_form.html",
        {
            "form": form,
        },
    )


# ============================================================
# PAYMENTS - READ ONLY
# ============================================================

@staff_member_required
def admin_payment_list(request):

    context = {
        "payments": (
            PaymentRecord.objects
            .select_related(
                "user",
                "exam",
                "track",
            )
        ),

        "users": (
            User.objects
            .filter(is_active=True)
        ),

        "exams": Exam.objects.all(),

        "tracks": ExamTrack.objects.all(),

        "coupons": (
            Coupon.objects
            .filter(is_active=True)
        ),
    }

    return render(
        request,
        "quiz/student/subscription/payment_list.html",
        context,
    )


# ============================================================
# TOGGLE EXAM PUBLISH STATUS
# ============================================================

@staff_member_required
@require_POST
def toggle_exam_publish(request):

    exam_id = request.POST.get(
        "exam_id"
    )

    try:

        exam = Exam.objects.get(
            id=exam_id
        )

        exam.is_published = (
            not exam.is_published
        )

        exam.save(
            update_fields=[
                "is_published",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "is_published": (
                    exam.is_published
                ),
            }
        )

    except Exam.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Exam not found",
            },
            status=404,
        )


# ============================================================
# ADMIN: MANUAL PAYMENT
# ============================================================

@staff_member_required
@require_POST
def admin_add_manual_payment(request):

    try:

        user_id = request.POST.get(
            "user_id"
        )

        exam_id = request.POST.get(
            "exam_id"
        )

        track_id = request.POST.get(
            "track_id"
        )

        plan_id = request.POST.get(
            "plan_id"
        )

        coupon_code = request.POST.get(
            "coupon"
        )

        reference_id = request.POST.get(
            "reference_id",
            "",
        )

        # ----------------------------------------------------
        # USER REQUIRED
        # ----------------------------------------------------

        if not user_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": "User is required",
                },
                status=400,
            )

        # ----------------------------------------------------
        # EXAM AND TRACK ARE MUTUALLY EXCLUSIVE
        # ----------------------------------------------------

        if exam_id and track_id:

            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Select either Exam or Track, "
                        "not both"
                    ),
                },
                status=400,
            )

        user = get_object_or_404(
            User,
            id=user_id,
        )

        exam = None
        track = None
        plan = None

        # ----------------------------------------------------
        # EXAM
        # ----------------------------------------------------

        if exam_id:

            exam = get_object_or_404(
                Exam,
                id=exam_id,
            )

        # ----------------------------------------------------
        # TRACK
        # ----------------------------------------------------

        if track_id:

            track = get_object_or_404(
                ExamTrack,
                id=track_id,
            )

            if not plan_id:

                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Subscription plan "
                            "is required for track"
                        ),
                    },
                    status=400,
                )

            plan = get_object_or_404(
                SubscriptionPlan,
                id=plan_id,
                is_active=True,
                tracks=track,
            )

        # ----------------------------------------------------
        # COUPON
        # ----------------------------------------------------

        coupon = None

        if coupon_code:

            coupon = (
                Coupon.objects
                .filter(
                    code=(
                        coupon_code
                        .strip()
                        .upper()
                    ),
                    is_active=True,
                )
                .first()
            )

        # ----------------------------------------------------
        # SINGLE PAYMENT SERVICE
        # ----------------------------------------------------

        PaymentService.apply_manual_payment(
            user=user,
            exam=exam,
            track=track,
            plan=plan,
            coupon=coupon,
            reference_id=reference_id,
        )

        return JsonResponse(
            {
                "success": True,
            }
        )

    except Exception as exc:

        logger.exception(
            "Manual payment failed"
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=500,
        )