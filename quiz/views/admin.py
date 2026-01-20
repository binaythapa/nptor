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
@staff_member_required
def recent_attempts_api(request):
    """
    Returns JSON of UserExam rows for page `page`.
    Query params:
      - page: int (1-indexed)
      - page_size: optional
      - q: optional filter string (username or exam.title)
    """
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 8))
    q = (request.GET.get('q') or '').strip()

    qs = UserExam.objects.select_related('user', 'exam').order_by('-started_at')
    if q:
        qs = qs.filter(Q(user__username__icontains=q) | Q(exam__title__icontains=q))

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    fmt = get_format('SHORT_DATETIME_FORMAT')
    rows = []
    for ue in page_obj.object_list:
        started = DateFormat(ue.started_at).format(fmt) if ue.started_at else ''
        if ue.submitted_at is None:
            score_text = "In progress"
        else:
            score_text = f"{round(ue.score or 0.0, 2)}%"
        rows.append({
            'id': ue.id,
            'user': ue.user.username,
            'exam': ue.exam.title,
            'started': started,
            'score': score_text,
            'status': 'in_progress' if ue.submitted_at is None else 'completed'
        })

    return JsonResponse({
        'results': rows,
        'has_next': page_obj.has_next(),
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'page': page,
        'page_size': page_size,
    })



