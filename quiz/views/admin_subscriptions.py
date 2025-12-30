import math
import random
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

# Project-specific imports
from quiz.forms import *
from quiz.models import (
    Exam,
    ExamTrack,
    UserExam,
    ExamSubscription,
    ExamTrackSubscription,
    Coupon,
)
from quiz.services.access import can_access_exam
from quiz.services.pricing import apply_coupon
from quiz.services.subscription import has_valid_subscription
from quiz.utils import get_leaf_category_name


# Re-assign User in case a custom user model is used (overrides the imported User if needed)
User = get_user_model()

# Logger
logger = logging.getLogger(__name__)



@staff_member_required
def subscription_admin_panel(request):
    context = {
        # Tracks & Exams
        "tracks": ExamTrack.objects.all().order_by("-created_at"),
        "exams": Exam.objects.select_related("track").all(),

        # Subscriptions
        "track_subs": (
            ExamTrackSubscription.objects
            .select_related("user", "track")
            .order_by("-subscribed_at")[:50]
        ),
        "exam_subs": (
            ExamSubscription.objects
            .select_related("user", "exam")
            .order_by("-subscribed_at")[:50]
        ),

        # Coupons
        "coupons": Coupon.objects.all().order_by("-valid_to"),

        # Meta
        "now": timezone.now(),
    }

    return render(
        request,
        "quiz/admin_subscription_panel.html",
        context,
    )


# -----------------------------------------
# INLINE TOGGLE TRACK
# -----------------------------------------
@staff_member_required
@require_POST
def toggle_track_status(request):
    track_id = request.POST.get("track_id")

    try:
        track = ExamTrack.objects.get(id=track_id)
        track.is_active = not track.is_active
        track.save()
        return JsonResponse({
            "success": True,
            "new_status": track.is_active
        })
    except ExamTrack.DoesNotExist:
        return JsonResponse({"success": False})


# -----------------------------------------
# INLINE TOGGLE COUPON
# -----------------------------------------
@staff_member_required
@require_POST
def toggle_coupon_status(request):
    coupon_id = request.POST.get("coupon_id")

    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.is_active = not coupon.is_active
        coupon.save()
        return JsonResponse({
            "success": True,
            "new_status": coupon.is_active
        })
    except Coupon.DoesNotExist:
        return JsonResponse({"success": False})
    

    


# -----------------------------------------
# CREATE COUPON (MODAL)
# -----------------------------------------
@staff_member_required
@require_POST
def create_coupon_ajax(request):
    code = request.POST.get("code").upper()
    percent_off = request.POST.get("percent_off") or None
    flat_off = request.POST.get("flat_off") or None
    valid_days = int(request.POST.get("valid_days", 7))

    if Coupon.objects.filter(code=code).exists():
        return JsonResponse({
            "success": False,
            "error": "Coupon already exists"
        })

    Coupon.objects.create(
        code=code,
        percent_off=int(percent_off) if percent_off else None,
        flat_off=Decimal(flat_off) if flat_off else None,
        valid_from=timezone.now(),
        valid_to=timezone.now() + timezone.timedelta(days=valid_days),
        is_active=True
    )

    return JsonResponse({"success": True})




@staff_member_required
@require_POST
def update_track_pricing(request):
    track_id = request.POST.get("track_id")
    is_free = request.POST.get("is_free") == "true"
    price = request.POST.get("price")

    try:
        track = ExamTrack.objects.get(id=track_id)

        if is_free:
            track.is_free = True
            track.price = 0
        else:
            if not price:
                return JsonResponse({
                    "success": False,
                    "error": "Price is required for paid tracks"
                })
            track.is_free = False
            track.price = Decimal(price)

        track.save()

        return JsonResponse({
            "success": True,
            "is_free": track.is_free,
            "price": str(track.price),
        })

    except ExamTrack.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Track not found"
        })






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
    

    




