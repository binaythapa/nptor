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


@login_required
@require_POST
def subscribe_track(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id)

    coupon_code = request.POST.get("coupon")
    price = track.lifetime_price or 0

    final_price, error = apply_coupon(price, coupon_code)

    if error:
        messages.error(request, error)
        return redirect("quiz:exam_list")

    ExamTrackSubscription.objects.create(
        user=request.user,
        track=track,
        is_active=True,
        payment_required=final_price > 0,
        amount=final_price,
        expires_at=None  # lifetime
    )

    messages.success(request, "Subscription activated")
    return redirect("quiz:student_dashboard")

@login_required
@require_POST
def subscribe_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    sub, created = ExamSubscription.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={
            "is_active": True,
            "payment_required": False,
            "amount": 0,
            "currency": "INR",
        }
    )

    messages.success(request, "Exam subscribed successfully.")
    return redirect("quiz:exam_list")




@login_required
def subscribe_track_checkout(request, track_id):
    track = get_object_or_404(ExamTrack, id=track_id, is_active=True)

    base_price = track.price or 0
    coupon_code = request.POST.get("coupon")
    final_price, coupon = apply_coupon(base_price, coupon_code)

    # -------------------------------
    # ₹0 FLOW (FREE / COUPON / TRIAL)
    # -------------------------------
    if final_price == 0:
        ExamTrackSubscription.objects.update_or_create(
            user=request.user,
            track=track,
            defaults={
                "is_active": True,
                "payment_required": False,
                "amount": 0,
                "expires_at": timezone.now() + timezone.timedelta(days=7),
            }
        )

        if coupon:
            coupon.used_count += 1
            coupon.save()

        messages.success(request, "Subscription activated successfully!")
        return redirect("quiz:student_dashboard")

    # -------------------------------
    # PAID FLOW (Razorpay later)
    # -------------------------------
    return render(request, "quiz/checkout.html", {
        "track": track,
        "base_price": base_price,
        "final_price": final_price,
        "coupon_code": coupon_code,
    })
















