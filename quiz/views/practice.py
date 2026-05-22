import math
import random
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from quiz.models import QuestionFeedback

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
from courses.services.context import get_course_context
from courses.services.practice_completion import track_practice_completion

import logging
from core.utils.memory import get_memory_usage_mb

logger = logging.getLogger("django")

from django.template.loader import render_to_string
def practice(request):

    """
    BASIC PRACTICE (PUBLIC)
    + COURSE-AWARE PRACTICE (OPTIONAL)
    """

    mem = get_memory_usage_mb()

    if mem is not None:
        if mem > 350:
            logger.warning(f"⚠ Practice page high memory usage: {mem} MB")
        else:
            logger.info(f"Practice page memory usage: {mem} MB")

    # ================= COURSE CONTEXT =================
    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    is_from_course = bool(course_slug and lesson_id)

    lesson = None

    if is_from_course:
        from courses.models import Lesson

        lesson = Lesson.objects.select_related(
            "practice_domain",
            "practice_category",
            "course"
        ).filter(
            id=lesson_id
        ).first()

    # ================= DETERMINE ORG CONTEXT =================
    org = None

    if is_from_course and lesson and lesson.course:
        org = lesson.course.organization

    # ================= PER LESSON RESET =================
    if is_from_course and lesson:

        last_lesson_id = request.session.get(
            "course_practice_lesson_id"
        )

        if last_lesson_id != lesson.id:
            request.session.pop(
                "course_practice_initialized",
                None
            )

            request.session.pop(
                "course_practice_count",
                None
            )

        request.session["course_practice_lesson_id"] = lesson.id

    # ================= FORCE FILTERS =================
    if is_from_course and lesson:

        request.session["p_filters"] = {
            "domain": lesson.practice_domain_id,
            "category": lesson.practice_category_id,
            "difficulty": lesson.practice_difficulty,
        }

    # ================= RESET =================
    if request.GET.get("reset") == "1":

        for k in [
            "p_seen",
            "p_qid",
            "p_filters",
            "p_total",
            "p_anon_count",
            "course_practice_initialized",
            "course_practice_count",
        ]:
            request.session.pop(k, None)

        return redirect("quiz:practice")

    # ================= READ FILTERS =================
    domain_id = (
        request.POST.get("domain")
        or request.GET.get("domain")
    )

    category_id = (
        request.POST.get("category")
        or request.GET.get("category")
    )

    difficulty = (
        request.POST.get("difficulty")
        or request.GET.get("difficulty")
    )

    if (
        is_from_course
        and lesson
        and lesson.practice_lock_filters
    ):

        filters = request.session.get("p_filters", {})

        domain_id = filters.get("domain")
        category_id = filters.get("category")
        difficulty = filters.get("difficulty")

    filters = {
        "domain": domain_id,
        "category": category_id,
        "difficulty": difficulty,
    }

    last_filters = request.session.get("p_filters")

    # ================= BASE QUERYSET =================
    qs = (
        Question.objects
        .filter(
            question_type__in=[
                Question.SINGLE,
                Question.MULTI,
                Question.TRUE_FALSE,
            ],
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("choices")
    )

    # ================= ORG / PUBLIC FILTER =================
    if org:
        qs = qs.filter(
            category__domain__organization=org
        )
    else:
        qs = qs.filter(
            category__domain__organization__isnull=True
        )

    # ================= DOMAIN FILTER =================
    selected_domain = None

    if domain_id and str(domain_id).isdigit():

        domain_filter = {
            "id": domain_id,
            "is_active": True
        }

        if org:
            domain_filter["organization"] = org
        else:
            domain_filter["organization__isnull"] = True

        selected_domain = Domain.objects.filter(
            **domain_filter
        ).first()

    # ================= CATEGORY FILTER =================
    if category_id and str(category_id).isdigit():

        cat = Category.objects.filter(
            id=category_id,
            is_active=True
        ).first()

        if cat:

            # =====================================
            # INCLUDE:
            # - selected category
            # - descendants
            # - all ancestors
            # =====================================

            cat_ids = set(
                cat.get_descendants_include_self()
            )

            ancestor = cat.parent

            while ancestor:
                cat_ids.add(ancestor.id)
                ancestor = ancestor.parent

            qs = qs.filter(
                category_id__in=cat_ids
            )

    # ================= DIFFICULTY =================
    if difficulty:
        qs = qs.filter(
            difficulty=difficulty
        )

    # ================= RESET IF FILTERS CHANGED =================
    if not is_from_course and filters != last_filters:

        request.session["p_filters"] = filters
        request.session["p_seen"] = []

        request.session.pop("p_qid", None)

        request.session["p_total"] = qs.count()

        request.session["p_anon_count"] = 0

    seen = request.session.get("p_seen", [])

    total = request.session.get(
        "p_total",
        qs.count()
    )

    anon_count = request.session.get(
        "p_anon_count",
        0
    )

    # ================= ANONYMOUS LIMIT =================
    if not request.user.is_authenticated:

        if anon_count >= settings.BASICS_ANON_LIMIT:

            return render(
                request,
                "quiz/student/practice/practice.html",
                {
                    "anon_limit_reached": True,
                    "anon_limit": settings.BASICS_ANON_LIMIT,

                    "domains": Domain.objects.filter(
                        is_active=True,
                        organization__isnull=True
                    ),

                    "categories": Category.objects.none(),

                    "difficulty_choices":
                        Question.DIFFICULTY_CHOICES,
                }
            )

    # ================= REMAINING =================
    remaining = qs.exclude(id__in=seen)

    # ================= COMPLETED =================
    if not remaining.exists():

        return render(
            request,
            "quiz/student/practice/practice.html",
            {
                "completed": True,

                "progress_done": total,
                "progress_total": total,

                "domains": Domain.objects.filter(
                    is_active=True,
                    organization__isnull=True
                ),

                "categories": Category.objects.none(),

                "difficulty_choices":
                    Question.DIFFICULTY_CHOICES,
            }
        )

    # ================= PICK QUESTION =================
    qid = request.session.get("p_qid")

    question = (
        remaining.filter(id=qid).first()
        if qid else None
    )

    if not question:

        question = remaining.order_by("?").first()

        request.session["p_qid"] = question.id

    # ================= SHUFFLE CHOICES =================
    choices = list(question.choices.all())

    random.seed(question.id)

    random.shuffle(choices)

    # ================= SKIP =================
    if (
        request.method == "POST"
        and request.POST.get("skip") == "1"
    ):

        seen.append(question.id)

        request.session["p_seen"] = seen

        request.session.pop("p_qid", None)

        return redirect(
            request.path + "?"
            + request.META.get("QUERY_STRING", "")
        )

    # ================= ANSWER CHECK =================
    result = None
    show_next = False

    selected_choice_id = None
    selected_multi_ids = []

    if (
        request.method == "POST"
        and request.POST.get("next") != "1"
    ):

        correct_choices = [
            c for c in choices if c.is_correct
        ]

        if question.question_type == Question.MULTI:

            selected_multi_ids = list(
                map(
                    int,
                    request.POST.getlist("choice_multi")
                )
            )

            correct_ids = [
                c.id for c in correct_choices
            ]

            result = (
                "correct"
                if set(selected_multi_ids)
                   == set(correct_ids)
                else "wrong"
            )

            show_next = result == "correct"

        else:

            selected_choice_id = request.POST.get(
                "choice"
            )

            selected = next(
                (
                    c for c in choices
                    if str(c.id)
                    == str(selected_choice_id)
                ),
                None
            )

            result = (
                "correct"
                if selected and selected.is_correct
                else "wrong"
            )

            show_next = result == "correct"

    # ================= NEXT =================
    if (
        request.method == "POST"
        and request.POST.get("next") == "1"
    ):

        course_slug, lesson, threshold = (
            get_course_context(request)
        )

        if lesson:

            count = track_practice_completion(
                request,
                lesson
            )

            if threshold and count >= threshold:

                return redirect(
                    "courses:course_learn_lesson",
                    slug=course_slug,
                    lesson_id=lesson.id
                )

        seen.append(question.id)

        request.session["p_seen"] = seen

        request.session.pop("p_qid", None)

        if not request.user.is_authenticated:

            request.session["p_anon_count"] = (
                anon_count + 1
            )

        return redirect(
            request.path + "?"
            + request.META.get("QUERY_STRING", "")
        )

    # ================= DISCUSSIONS =================
    discussions = (
        QuestionDiscussion.objects
        .filter(
            question=question,
            is_deleted=False
        )
        .annotate(score=Sum("votes__value"))
        .order_by(
            "-is_pinned",
            "-score",
            "created_at"
        )
    )

    categories = (
        Category.objects.filter(
            domain=selected_domain,
            is_active=True
        )
        if selected_domain
        else Category.objects.none()
    )

    # ================= FINAL RENDER =================
    return render(
        request,
        "quiz/student/practice/practice.html",
        {
            "question": question,
            "choices": choices,

            "result": result,

            "selected_choice_id":
                selected_choice_id,

            "selected_multi_ids":
                selected_multi_ids,

            "show_next": show_next,

            "explanation":
                question.explanation,

            "discussions": discussions,

            "domains": Domain.objects.filter(
                is_active=True,
                organization__isnull=True
            ),

            "categories": categories,

            "domain_id": domain_id,
            "category_id": category_id,
            "difficulty": difficulty,

            "difficulty_choices":
                Question.DIFFICULTY_CHOICES,

            "progress_done": len(seen),
            "progress_total": total,

            "is_from_course": is_from_course,
        }
    )
@require_POST
@login_required
def practice_feedback_ajax(request):

    try:
        question_id = request.POST.get("question_id")
        comment = (request.POST.get("student_comment") or "").strip()
        is_incorrect = request.POST.get("answer_incorrect") in ["1", "true", "on"]

        if not question_id:
            return JsonResponse({
                "success": False,
                "message": "Invalid question."
            })

        if not comment and not is_incorrect:
            return JsonResponse({
                "success": False,
                "message": "Please write a comment or mark as incorrect/confusing."
            })

        question = Question.objects.get(id=question_id)

        QuestionFeedback.objects.create(
            user=request.user,
            question=question,
            comment=comment,
            is_answer_incorrect=is_incorrect
        )

        return JsonResponse({
            "success": True,
            "message": "Feedback submitted successfully."
        })

    except Question.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Question not found."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Server error: {str(e)}"
        })







from django.http import JsonResponse
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
@require_POST
@login_required
def discussion_vote(request):
    discussion_id = request.POST.get("discussion_id")
    value = request.POST.get("value")

    if not discussion_id or value not in ["1", "-1"]:
        return JsonResponse({"success": False})

    discussion = get_object_or_404(
        QuestionDiscussion,
        id=discussion_id,
        is_deleted=False
    )

    DiscussionVote.objects.update_or_create(
        user=request.user,
        discussion=discussion,
        defaults={"value": int(value)}
    )

    score = discussion.votes.aggregate(
        s=Sum("value")
    )["s"] or 0

    return JsonResponse({
        "success": True,
        "score": score
    })




@require_POST
def practice_answer_ajax(request):
    question_id = request.POST.get("question_id")

    question = get_object_or_404(
        Question,
        id=question_id,
        is_active=True,
        is_deleted=False
    )

    choices = question.choices.order_by("order", "id")

    result = "wrong"
    show_next = False
    selected_choice_id = None
    selected_multi_ids = []

    correct_ids = list(
        choices.filter(is_correct=True)
        .values_list("id", flat=True)
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
        "quiz/practice/_answer_result.html",
        {
            "question": question,
            "choices": choices,
            "result": result,
            "selected_choice_id": selected_choice_id,
            "selected_multi_ids": selected_multi_ids,
            "show_next": show_next,
            "explanation": question.explanation,   # 👈 MUST BE HERE
        },
        request=request
    )

    return JsonResponse({
        "success": True,
        "html": html
    })




from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.db.models import Q

@require_POST
def practice_next_ajax(request):
    """
    AJAX: Move to next question

    Supports:
    - Parent category questions
    - Child category questions
    - Cross-domain parent categories
    - Course threshold logic
    - Session tracking
    """

    # =====================================
    # UPDATE SESSION STATE
    # =====================================
    seen = request.session.get("p_seen", [])
    qid = request.session.get("p_qid")

    if qid:
        seen.append(qid)
        request.session["p_seen"] = seen
        request.session.pop("p_qid", None)

    # =====================================
    # COURSE THRESHOLD CHECK
    # =====================================
    course_slug, lesson, threshold = get_course_context(request)

    if lesson:
        count = track_practice_completion(request, lesson)

        if threshold and count >= threshold:
            return JsonResponse({
                "success": True,
                "redirect": reverse(
                    "courses:course_learn_lesson",
                    kwargs={
                        "slug": course_slug,
                        "lesson_id": lesson.id
                    }
                )
            })

    # =====================================
    # READ FILTERS FROM SESSION
    # =====================================
    filters = request.session.get("p_filters", {})

    domain_id = filters.get("domain")
    category_id = filters.get("category")
    difficulty = filters.get("difficulty")

    # =====================================
    # BASE QUERYSET
    # =====================================
    qs = (
        Question.objects
        .filter(
            question_type__in=[
                Question.SINGLE,
                Question.MULTI,
                Question.TRUE_FALSE,
            ],
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("choices")
    )

    # =====================================
    # DOMAIN OBJECT
    # =====================================
    selected_domain = None

    if domain_id and str(domain_id).isdigit():

        selected_domain = Domain.objects.filter(
            id=domain_id,
            is_active=True
        ).first()

    # =====================================
    # CATEGORY FILTER
    # =====================================
    if category_id and str(category_id).isdigit():

        cat = Category.objects.filter(
            id=category_id,
            is_active=True
        ).first()

        if cat:

            # Include:
            # - selected category
            # - descendants
            cat_ids = list(cat.get_descendants_include_self())

            # Include parent category
            if cat.parent:
                cat_ids.append(cat.parent.id)

            qs = qs.filter(category_id__in=cat_ids)

            # Handle cross-domain hierarchy
            if selected_domain:

                qs = qs.filter(
                    Q(category__domain=selected_domain) |
                    Q(category__parent__domain=selected_domain) |
                    Q(category__id=cat.id) |
                    Q(category__parent_id=cat.id)
                )

    # =====================================
    # DIFFICULTY FILTER
    # =====================================
    if difficulty:
        qs = qs.filter(difficulty=difficulty)

    # =====================================
    # REMOVE SEEN QUESTIONS
    # =====================================
    remaining = qs.exclude(id__in=seen)

    # =====================================
    # COMPLETED
    # =====================================
    if not remaining.exists():

        html = render_to_string(
            "quiz/practice/_practice_completed.html",
            {},
            request=request
        )

        return JsonResponse({
            "success": True,
            "html": html
        })

    # =====================================
    # PICK RANDOM QUESTION
    # =====================================
    question = remaining.order_by("?").first()

    request.session["p_qid"] = question.id

    # =====================================
    # RENDER HTML
    # =====================================
    html = render_to_string(
        "quiz/practice/_practice_question.html",
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





@require_POST
@login_required
def discussion_submit_ajax(request):
    content = (request.POST.get("student_comment") or "").strip()
    question_id = request.POST.get("question_id")
    parent_id = request.POST.get("parent_id")

    if not content:
        return JsonResponse({"success": False, "message": "Empty comment"})

    question = get_object_or_404(
        Question,
        id=question_id,
        is_active=True,
        is_deleted=False
    )

    parent = None
    if parent_id:
        parent = QuestionDiscussion.objects.filter(
            id=parent_id,
            question=question,
            is_deleted=False
        ).first()

    discussion = QuestionDiscussion.objects.create(
        user=request.user,
        question=question,
        parent=parent,
        content=content
    )

    html = render_to_string(
        "quiz/practice/_discussion_item.html",   # ✅ updated path
        {"d": discussion},
        request=request
    )

    return JsonResponse({
        "success": True,
        "html": html
    })
