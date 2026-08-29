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
    Coupon,
)
from quiz.services.access import can_access_exam
from quiz.services.pricing import apply_coupon

from quiz.utils import get_leaf_category_name


# Re-assign User in case a custom user model is used (overrides the imported User if needed)
User = get_user_model()

# Logger
logger = logging.getLogger(__name__)

# ============================================================
# NOTIFICATIONS
# ============================================================

@login_required
def notifications_list(request):
    """
    Display notifications available to the current user.

    A notification is visible when:

        1. It is a broadcast notification
           (users field is empty)

        OR

        2. The notification explicitly targets
           the current user.
    """

    notifications = (
        Notification.objects
        .order_by("-created_at")
    )

    visible = []

    for notification in notifications:

        # ----------------------------------------------------
        # Determine visibility
        # ----------------------------------------------------

        is_visible = (
            not notification.users.exists()
            or notification.users.filter(
                id=request.user.id
            ).exists()
        )

        if not is_visible:
            continue

        # ----------------------------------------------------
        # Add transient template property
        # ----------------------------------------------------

        notification.is_unread = (
            notification.unread_for(request.user)
        )

        visible.append(notification)

    # --------------------------------------------------------
    # Unread count
    # --------------------------------------------------------

    unread_count = sum(
        1
        for notification in visible
        if notification.is_unread
    )

    return render(
        request,
        "quiz/notifications_list.html",
        {
            "notifications": visible,
            "unread_count": unread_count,
        },
    )


# ============================================================
# READ ONE NOTIFICATION
# ============================================================

@login_required
def notification_read(request, pk):
    """
    Mark one notification as read and display it.
    """

    notification = get_object_or_404(
        Notification,
        pk=pk,
    )

    # --------------------------------------------------------
    # Security
    # --------------------------------------------------------

    is_visible = (
        not notification.users.exists()
        or notification.users.filter(
            id=request.user.id
        ).exists()
    )

    if not is_visible:
        raise PermissionDenied(
            "You do not have access to this notification."
        )

    # --------------------------------------------------------
    # Mark read
    # --------------------------------------------------------

    notification.mark_read(
        request.user
    )

    return render(
        request,
        "quiz/notification_detail.html",
        {
            "notification": notification,
        },
    )


# ============================================================
# MARK ALL NOTIFICATIONS AS READ
# ============================================================

@login_required
def notifications_mark_all(request):
    """
    Mark all visible notifications as read.
    """

    if request.method != "POST":
        return redirect(
            "quiz:notifications_list"
        )

    notifications = (
        Notification.objects
        .order_by("-created_at")[:200]
    )

    for notification in notifications:

        is_visible = (
            not notification.users.exists()
            or notification.users.filter(
                id=request.user.id
            ).exists()
        )

        if not is_visible:
            continue

        if notification.unread_for(
            request.user
        ):

            notification.mark_read(
                request.user
            )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "/",
        )
    )
