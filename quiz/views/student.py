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



from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum

from quiz.models import (
    Question,
    Category,
    Domain,
    QuestionDiscussion,
)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
def practice(request):
    """
    BASIC PRACTICE (PUBLIC)
    """

    # =====================================================
    # RESET
    # =====================================================
    if request.GET.get("reset") == "1":
        for k in ["p_seen", "p_qid", "p_filters", "p_total", "p_anon_count"]:
            request.session.pop(k, None)
        return redirect("quiz:practice")

    # =====================================================
    # READ FILTERS
    # =====================================================
    domain_id = request.POST.get("domain") or request.GET.get("domain")
    category_id = request.POST.get("category") or request.GET.get("category")
    difficulty = request.POST.get("difficulty") or request.GET.get("difficulty")

    filters = {
        "domain": domain_id,
        "category": category_id,
        "difficulty": difficulty,
    }

    last_filters = request.session.get("p_filters")

    # =====================================================
    # BASE QUERYSET
    # =====================================================
    qs = (
        Question.objects
        .filter(
            question_type__in=[
                Question.SINGLE,
                Question.MULTI,
                Question.TRUE_FALSE,
            ],
            is_active=True,
            is_deleted= False,
        )
        .prefetch_related("choices")
    )

    selected_domain = None

    if domain_id and domain_id.isdigit():
        selected_domain = Domain.objects.filter(
            id=domain_id,
            is_active=True
        ).first()

        if selected_domain:
            qs = qs.filter(category__domain=selected_domain)

    if category_id and category_id.isdigit() and selected_domain:
        cat = Category.objects.filter(
            id=category_id,
            domain=selected_domain,
            is_active=True
        ).first()

        if cat:
            qs = qs.filter(
                category_id__in=cat.get_descendants_include_self()
            )

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # =====================================================
    # RESET SESSION IF FILTERS CHANGED
    # =====================================================
    if filters != last_filters:
        request.session["p_filters"] = filters
        request.session["p_seen"] = []
        request.session.pop("p_qid", None)
        request.session["p_total"] = qs.count()

    seen = request.session.get("p_seen", [])
    total = request.session.get("p_total", qs.count())

    # =====================================================
    # REMAINING QUESTIONS
    # =====================================================
    remaining = qs.exclude(id__in=seen)

    if not remaining.exists():
        return render(request, "quiz/practice.html", {
            "completed": True,
            "progress_done": total,
            "progress_total": total,
            "domains": Domain.objects.filter(is_active=True),
            "categories": Category.objects.none(),
            "difficulty_choices": Question.DIFFICULTY_CHOICES,
        })

    # =====================================================
    # PICK QUESTION
    # =====================================================
    qid = request.session.get("p_qid")
    question = remaining.filter(id=qid).first() if qid else None

    if not question:
        question = remaining.order_by("?").first()
        request.session["p_qid"] = question.id

    choices = question.choices.order_by("order", "id")

    # =====================================================
    # 🆕 SKIP QUESTION (SAFE & ISOLATED)
    # =====================================================
    if request.method == "POST" and request.POST.get("skip") == "1":
        seen.append(question.id)
        request.session["p_seen"] = seen
        request.session.pop("p_qid", None)

        return redirect(
            request.path + "?" + request.META.get("QUERY_STRING", "")
        )

    # =====================================================
    # FEEDBACK STATUS (UI CONTROL)
    # =====================================================
    feedback_submitted = False
    if request.user.is_authenticated:
        feedback_submitted = QuestionDiscussion.objects.filter(
            user=request.user,
            question=question,
            discussion_type=QuestionDiscussion.TYPE_DOUBT,
        ).exists()

    # =====================================================
    # 🚩 FEEDBACK SUBMIT
    # =====================================================
    if (
        request.method == "POST"
        and request.POST.get("feedback_submit") == "1"
        and request.user.is_authenticated
    ):
        content = (request.POST.get("student_comment") or "").strip()
        is_incorrect = bool(request.POST.get("answer_incorrect"))

        if content or is_incorrect:
            QuestionDiscussion.objects.get_or_create(
                user=request.user,
                question=question,
                discussion_type=QuestionDiscussion.TYPE_DOUBT,
                defaults={
                    "content": content or "Flagged as incorrect/confusing",
                    "is_answer_incorrect": is_incorrect,
                }
            )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok"})

        return redirect(
            request.path + "?" + request.META.get("QUERY_STRING", "")
        )

    # =====================================================
    # STATE
    # =====================================================
    result = None
    show_next = False
    correct_choices = choices.filter(is_correct=True)
    selected_choice_id = None
    selected_multi_ids = []

    # =====================================================
    # SUBMIT ANSWER
    # =====================================================
    if request.method == "POST" and request.POST.get("next") != "1":

        if question.question_type == Question.MULTI:
            selected_multi_ids = list(
                map(int, request.POST.getlist("choice_multi"))
            )
            correct_ids = list(
                correct_choices.values_list("id", flat=True)
            )
            result = (
                "correct"
                if set(selected_multi_ids) == set(correct_ids)
                else "wrong"
            )
            show_next = result == "correct"

        else:
            selected_choice_id = request.POST.get("choice")
            selected = choices.filter(id=selected_choice_id).first()
            result = (
                "correct"
                if selected and selected.is_correct
                else "wrong"
            )
            show_next = result == "correct"

    # =====================================================
    # NEXT
    # =====================================================
    if request.method == "POST" and request.POST.get("next") == "1":
        seen.append(question.id)
        request.session["p_seen"] = seen
        request.session.pop("p_qid", None)
        return redirect(
            request.path + "?" + request.META.get("QUERY_STRING", "")
        )

    # =====================================================
    # DISCUSSIONS
    # =====================================================
    discussions = (
        QuestionDiscussion.objects
        .filter(question=question, is_deleted=False)
        .annotate(score=Sum("votes__value"))
        .order_by("-is_pinned", "-score", "created_at")
    )

    categories = (
        Category.objects.filter(
            domain=selected_domain,
            is_active=True,
        )
        if selected_domain
        else Category.objects.none()
    )

    # =====================================================
    # RENDER
    # =====================================================
    return render(request, "quiz/practice.html", {
        "question": question,
        "choices": choices,
        "result": result,
        "selected_choice_id": selected_choice_id,
        "selected_multi_ids": selected_multi_ids,
        "show_next": show_next,
        "explanation": question.explanation,
        "discussions": discussions,
        "feedback_submitted": feedback_submitted,
        "domains": Domain.objects.filter(is_active=True),
        "categories": categories,
        "domain_id": domain_id,
        "category_id": category_id,
        "difficulty": difficulty,
        "difficulty_choices": Question.DIFFICULTY_CHOICES,
        "progress_done": len(seen),
        "progress_total": total,
    })




@require_POST
@login_required
def practice_feedback_ajax(request):
    question_id = request.POST.get("question_id")
    comment = (request.POST.get("student_comment") or "").strip()
    is_incorrect = request.POST.get("answer_incorrect") == "on"

    if not question_id or not comment:
        return JsonResponse({
            "success": False,
            "message": "Comment cannot be empty."
        })

    question = get_object_or_404(Question, id=question_id)

    # Prevent duplicate feedback by same user
    if QuestionFeedback.objects.filter(
        user=request.user,
        question=question
    ).exists():
        return JsonResponse({
            "success": False,
            "message": "You already submitted feedback for this question."
        })

    QuestionFeedback.objects.create(
        user=request.user,
        question=question,
        comment=comment,
        is_answer_incorrect=is_incorrect
    )

    return JsonResponse({
        "success": True,
        "message": "Thank you! Your feedback was submitted."
    })



from django.http import JsonResponse
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@require_POST
@login_required
def discussion_vote(request):
    discussion_id = request.POST.get("discussion_id")
    value = int(request.POST.get("value"))

    discussion = get_object_or_404(QuestionDiscussion, id=discussion_id)

    DiscussionVote.objects.update_or_create(
        user=request.user,
        discussion=discussion,
        defaults={"value": value}
    )

    score = discussion.votes.aggregate(
        s=Sum("value")
    )["s"] or 0

    return JsonResponse({
        "success": True,
        "score": score
    })


from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# ============================================
# AJAX ANSWER SUBMIT
# ============================================
@require_POST
def practice_answer_ajax(request):
    question_id = request.POST.get("question_id")
    question = get_object_or_404(Question, id=question_id)
    choices = question.choices.order_by("order", "id")

    result = "wrong"
    show_next = False
    selected_choice_id = None
    selected_multi_ids = []

    correct_ids = list(
        choices.filter(is_correct=True).values_list("id", flat=True)
    )

    if question.question_type == Question.MULTI:
        selected_multi_ids = list(
            map(int, request.POST.getlist("choice_multi"))
        )
        if set(selected_multi_ids) == set(correct_ids):
            result = "correct"
            show_next = True

    else:
        selected_choice_id = request.POST.get("choice")
        if selected_choice_id and int(selected_choice_id) in correct_ids:
            result = "correct"
            show_next = True

    html = render_to_string(
        "quiz/_answer_result.html",
        {
            "question": question,
            "choices": choices,
            "result": result,
            "selected_choice_id": selected_choice_id,
            "selected_multi_ids": selected_multi_ids,
            "show_next": show_next,
        },
        request=request
    )

    return JsonResponse({
        "success": True,
        "result": result,
        "show_next": show_next,
        "html": html
    })

from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string

@require_POST
def practice_next_ajax(request):
    """
    AJAX: Move to next practice question safely
    """

    # ===============================
    # SESSION STATE (same as practice)
    # ===============================
    seen = request.session.get("p_seen", [])
    qid = request.session.get("p_qid")

    if qid:
        seen.append(qid)
        request.session["p_seen"] = seen
        request.session.pop("p_qid", None)

    # ===============================
    # REBUILD QUERYSET (same filters)
    # ===============================
    domain_id = request.session.get("p_filters", {}).get("domain")
    category_id = request.session.get("p_filters", {}).get("category")
    difficulty = request.session.get("p_filters", {}).get("difficulty")

    qs = Question.objects.filter(
        question_type__in=[
            Question.SINGLE,
            Question.MULTI,
            Question.TRUE_FALSE,
        ]
    ).prefetch_related("choices")

    if domain_id and str(domain_id).isdigit():
        qs = qs.filter(category__domain_id=domain_id)

    if category_id and str(category_id).isdigit():
        qs = qs.filter(category_id=category_id)

    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    remaining = qs.exclude(id__in=seen)

    # ===============================
    # NO MORE QUESTIONS
    # ===============================
    if not remaining.exists():
        html = render_to_string(
            "quiz/_practice_completed.html",
            {},
            request=request
        )
        return JsonResponse({"success": True, "html": html})

    # ===============================
    # PICK NEXT QUESTION
    # ===============================
    question = remaining.order_by("?").first()
    request.session["p_qid"] = question.id

    html = render_to_string(
        "quiz/_practice_question.html",
        {
            "question": question,
            "choices": question.choices.order_by("order", "id"),
            "explanation": question.explanation,
        },
        request=request
    )

    return JsonResponse({
        "success": True,
        "html": html
    })


# ============================================
# AJAX DISCUSSION SUBMIT (COMMENT / REPLY)
# ============================================
@require_POST
@login_required
def discussion_submit_ajax(request):
    content = (request.POST.get("student_comment") or "").strip()
    question_id = request.POST.get("question_id")
    parent_id = request.POST.get("parent_id")

    if not content:
        return JsonResponse({"success": False, "message": "Empty comment"})

    discussion = QuestionDiscussion.objects.create(
        user=request.user,
        question_id=question_id,
        parent_id=parent_id or None,
        content=content
    )

    html = render_to_string(
        "quiz/_discussion_item.html",
        {"d": discussion},
        request=request
    )

    return JsonResponse({
        "success": True,
        "html": html
    })


#########################################




@require_GET
def practice_express_next(request):

    # -------------------------------
    # READ FILTERS
    # -------------------------------
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

    # -------------------------------
    # BASE QUERYSET (🔥 FIXED)
    # ❌ REMOVED question_type filter
    # -------------------------------
    qs = Question.objects.filter(
        category__isnull=False ,
        is_active= True
    ).prefetch_related("choices")

    # -------------------------------
    # DOMAIN FILTER
    # -------------------------------
    if domain_id:
        qs = qs.filter(category__domain_id=domain_id)

    # -------------------------------
    # CATEGORY FILTER (DESCENDANTS)
    # -------------------------------
    if category_id:
        cat = Category.objects.filter(
            id=category_id,
            domain_id=domain_id,
            is_active=True
        ).first()
        if cat:
            qs = qs.filter(
                category_id__in=cat.get_descendants_include_self()
            )

    # -------------------------------
    # DIFFICULTY FILTER
    # -------------------------------
    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # -------------------------------
    # RESET WHEN FILTERS CHANGE
    # -------------------------------
    if current_filters != last_filters:
        request.session["pe_filters"] = current_filters
        request.session["pe_seen_qids"] = []
        request.session["pe_total"] = qs.count()
        request.session["pe_anon_attempted"] = 0

    seen_qids = request.session.get("pe_seen_qids", [])
    total_questions = request.session.get("pe_total", qs.count())
    anon_attempted = request.session.get("pe_anon_attempted", 0)

    # -------------------------------
    # NO QUESTIONS
    # -------------------------------
    if total_questions == 0:
        return JsonResponse({
            "no_questions": True,
            "progress_done": 0,
            "progress_total": 0,
        })

    # -------------------------------
    # 🔒 ANON LIMIT (SETTINGS)
    # -------------------------------
    if not request.user.is_authenticated:
        limit = getattr(settings, "EXPRESS_ANON_LIMIT", 0)

        if anon_attempted >= limit:
            return JsonResponse({
                "limit_reached": True,
                "message": f"Free limit of {limit} question(s) reached.Login to unlock unlimited access.",
                "progress_done": anon_attempted,
                "progress_total": limit,
            })

    # -------------------------------
    # REMAINING QUESTIONS
    # -------------------------------
    remaining = qs.exclude(id__in=seen_qids)

    # -------------------------------
    # COMPLETED
    # -------------------------------
    if not remaining.exists():
        request.session["pe_seen_qids"] = []
        return JsonResponse({
            "completed": True,
            "progress_done": total_questions,
            "progress_total": total_questions,
        })

    # -------------------------------
    # PICK NEXT QUESTION
    # -------------------------------
    question = remaining.order_by("?").first()
    correct_choices = question.choices.filter(is_correct=True)

    seen_qids.append(question.id)
    request.session["pe_seen_qids"] = seen_qids

    if not request.user.is_authenticated:
        request.session["pe_anon_attempted"] = anon_attempted + 1

    # -------------------------------
    # RESPONSE (🔥 SUPPORTS ALL TYPES)
    # -------------------------------
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


# =====================================================
# PRACTICE EXPRESS – SAVE RESULT (AJAX, LOGIN ONLY)
# =====================================================
@require_POST
@login_required
def practice_express_save(request):
    question_id = request.POST.get("question_id")
    is_correct = request.POST.get("is_correct") == "true"

    question = Question.objects.select_related("category").get(id=question_id)
    today = timezone.now().date()

    stat, _ = PracticeStat.objects.get_or_create(
        user=request.user,
        category=question.category
    )

    # streak logic
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
        "streak": stat.streak
    })



# =====================================================
# AJAX: LOAD CATEGORIES BY DOMAIN
# =====================================================
@require_GET
def ajax_categories_by_domain(request):
    domain_id = request.GET.get("domain")

    if not domain_id or not domain_id.isdigit():
        return JsonResponse({"categories": []})

    categories = Category.objects.filter(
        domain_id=domain_id,
        is_active=True
    ).values("id", "name", "parent_id")

    return JsonResponse({
        "categories": list(categories)
    })


# =====================================================
# PRACTICE EXPRESS – PAGE
# =====================================================

def practice_express(request):
    return render(request, "quiz/practice_express.html", {
        "domains": Domain.objects.filter(is_active=True),
        "categories": Category.objects.none(),
        "difficulty_choices": Question.DIFFICULTY_CHOICES,
    })
