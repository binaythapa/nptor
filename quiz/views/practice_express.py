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

from quiz.forms import *
from quiz.models import Exam, ExamTrack, UserExam, Coupon
from quiz.services.access import can_access_exam
from quiz.services.pricing import apply_coupon
from quiz.utils import get_leaf_category_name
from quiz.models import Question, Category, Domain, QuestionDiscussion
from courses.services.context import get_course_context
from courses.services.practice_completion import track_practice_completion
from core.utils.memory import get_memory_usage_mb

User = get_user_model()
logger = logging.getLogger("django")

from django.template.loader import render_to_string


@require_GET
def ajax_categories_by_domain(request):
    domain_id = request.GET.get("domain")

    if not domain_id or not domain_id.isdigit():
        return JsonResponse({"categories": []})

    categories = Category.objects.filter(
        domain_id=domain_id,
        domain__organization__isnull=True,
        is_active=True,
    ).values("id", "name", "parent_id")

    return JsonResponse({"categories": list(categories)})


# =====================================================
# PRACTICE EXPRESS – PAGE
# =====================================================
def practice_express(request):
    if request.GET.get("reset") == "1":
        for key in [
            "pe_seen", "pe_qid", "pe_filters", "pe_total", "pe_progress",
        ]:
            request.session.pop(key, None)
        request.session.modified = True
        return redirect("quiz:practice_express")

    return render(request, "quiz/student/practice_express/practice_express.html", {
        "domains": Domain.objects.filter(
            organization__isnull=True,
            is_active=True,
        ),
        "categories": Category.objects.none(),
        "difficulty_choices": Question.DIFFICULTY_CHOICES,
    })


@require_GET
def practice_express_next(request):
    domain_id = request.GET.get("domain")
    category_id = request.GET.get("category")
    difficulty = request.GET.get("difficulty")

    domain_id = domain_id if domain_id and domain_id.isdigit() else None
    category_id = category_id if category_id and category_id.isdigit() else None
    difficulty = difficulty if difficulty else None

    current_filters = {
        "domain": domain_id,
        "category": category_id,
        "difficulty": difficulty,
    }
    last_filters = request.session.get("pe_filters")

    qs = Question.objects.filter(
        is_active=True,
        is_deleted=False,
    ).prefetch_related("choices")

    selected_domain = None
    if domain_id:
        selected_domain = Domain.objects.filter(
            id=domain_id,
            organization__isnull=True,
            is_active=True,
        ).first()

        if not selected_domain:
            return JsonResponse({
                "no_questions": True,
                "progress_done": 0,
                "progress_total": 0,
            })

        qs = qs.filter(
            Q(primary_category__domain=selected_domain)
            | Q(categories__domain=selected_domain)
        ).distinct()

    if category_id and selected_domain:
        cat = Category.objects.filter(
            id=category_id,
            domain=selected_domain,
            is_active=True,
        ).first()
        if cat:
            category_ids = cat.get_descendants_include_self()
            qs = qs.filter(
                Q(primary_category_id__in=category_ids)
                | Q(categories__id__in=category_ids)
            ).distinct()

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    if current_filters != last_filters:
        request.session["pe_filters"] = current_filters
        request.session["pe_seen_qids"] = []
        request.session["pe_total"] = qs.count()
        request.session["pe_anon_attempted"] = 0

    seen_qids = request.session.get("pe_seen_qids", [])
    total_questions = request.session.get("pe_total", qs.count())
    anon_attempted = request.session.get("pe_anon_attempted", 0)

    if total_questions == 0:
        return JsonResponse({
            "no_questions": True,
            "progress_done": 0,
            "progress_total": 0,
        })

    if not request.user.is_authenticated:
        limit = getattr(settings, "EXPRESS_ANON_LIMIT", 0)
        if anon_attempted >= limit:
            return JsonResponse({
                "limit_reached": True,
                "message": f"Free limit of {limit} question(s) reached.Login to unlock unlimited access.",
                "progress_done": anon_attempted,
                "progress_total": limit,
            })

    remaining = qs.exclude(id__in=seen_qids)
    if not remaining.exists():
        request.session["pe_seen_qids"] = []
        return JsonResponse({
            "completed": True,
            "progress_done": total_questions,
            "progress_total": total_questions,
        })

    question = remaining.order_by("?").first()
    correct_choices = question.choices.filter(is_correct=True)

    seen_qids.append(question.id)
    request.session["pe_seen_qids"] = seen_qids
    if not request.user.is_authenticated:
        request.session["pe_anon_attempted"] = anon_attempted + 1

    return JsonResponse({
        "id": question.id,
        "text": question.text,
        "question_type": question.question_type,
        "explanation": question.explanation or "",
        "correct_choices": [c.id for c in correct_choices],
        "choices": [
            {"id": c.id, "text": c.text}
            for c in question.choices.all().order_by("order", "id")
        ],
        "progress_done": len(seen_qids),
        "progress_total": total_questions,
    })


@require_POST
@login_required
def practice_express_save(request):
    question_id = request.POST.get("question_id")
    is_correct = request.POST.get("is_correct") == "true"

    question = Question.objects.select_related("category").get(id=question_id)
    today = timezone.now().date()

    stat, _ = PracticeStat.objects.get_or_create(
        user=request.user,
        category=question.category,
    )

    if stat.last_practice_date == today:
        pass
    elif stat.last_practice_date == today - timezone.timedelta(days=1):
        stat.streak += 1
    else:
        stat.streak = 1

    stat.last_practice_date = today
    stat.total_attempted += 1
    if is_correct:
        stat.total_correct += 1
    stat.save()

    return JsonResponse({
        "total": stat.total_attempted,
        "correct": stat.total_correct,
        "accuracy": stat.accuracy(),
        "streak": stat.streak,
    })
