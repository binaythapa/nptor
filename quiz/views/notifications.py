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

# -------------------------
# Notifications
# -------------------------
@login_required
def notifications_list(request):
    qs = Notification.objects.order_by('-created_at')
    visible = []

    for n in qs:
        # add transient boolean for template convenience
        n.is_unread = n.unread_for(request.user)
        if (not n.users.exists()) or (request.user in n.users.all()):
            visible.append(n)

    return render(request, 'quiz/notifications_list.html', {'notifications': visible})


@login_required
def notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk)
    n.mark_read(request.user)
    return render(request, 'quiz/notification_detail.html', {'notification': n})


@login_required
def notifications_mark_all(request):
    qs = Notification.objects.order_by('-created_at')[:200]
    visible = [n for n in qs if (not n.users.exists()) or (request.user in n.users.all())]
    for n in visible:
        n.mark_read(request.user)
    return redirect(request.META.get('HTTP_REFERER', '/'))