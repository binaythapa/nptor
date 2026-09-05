import math
import random
import logging

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from quiz.services.exam_question_allocator import (
    allocate_questions_for_exam,
)

from subscriptions.models import (
    SubscriptionPlan,
    SubscriptionEntitlement,
)

from subscriptions.services import (
    SubscriptionService,
    AccessService,
)

from organizations.models.access import ResourceAccess



from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import (
    login,
    authenticate,
    get_user_model,
)
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.contrib.auth.forms import UserCreationForm
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
from django.http import (
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import (
    get_object_or_404,
    render,
    redirect,
)
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format
from django.views.decorators.http import (
    require_GET,
    require_POST,
)
from django.views.generic import (
    CreateView,
    DetailView,
    TemplateView,
    UpdateView,
)

# ============================================================
# PROJECT IMPORTS
# ============================================================

from courses.models import (
    Course,
    Lesson,
)

from courses.services.progress import (
    get_next_lesson,
)

from courses.services.quiz_completion import *

from quiz.forms import *

from quiz.models import (
    Exam,
    ExamTrack,
    UserExam,
    UserAnswer,
    Question,
    QuestionFeedback,
    Coupon,
)

from quiz.services.access import (
    can_access_exam,
)

from quiz.services.pricing import (
    apply_coupon,
)

from quiz.services.grading import (
    grade_exam,
)

from quiz.services.answer_persistence import (
    autosave_answers,
)

from quiz.utils import (
    get_leaf_category_name,
)

# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()

# ============================================================
# UTILITIES
# ============================================================

from core.utils.memory import (
    get_memory_usage_mb,
)

logger = logging.getLogger("django")

@login_required
def exam_start(request, exam_id):
    mem = get_memory_usage_mb()

    if mem is not None:
        logger.info(
            f"Exam Start page memory usage: {mem} MB"
        )

    # =========================================================
    # LOAD EXAM
    # =========================================================

    exam = get_object_or_404(
        Exam,
        pk=exam_id,
        is_published=True,
    )

    # =========================================================
    # COURSE CONTEXT
    # =========================================================

    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    if course_slug and lesson_id:

        from courses.models import Lesson

        lesson = (
            Lesson.objects
            .filter(
                id=lesson_id,
                lesson_type=Lesson.TYPE_QUIZ,
                exam=exam,
            )
            .first()
        )

        if lesson:

            # -------------------------------------------------
            # COURSE QUIZ MAX ATTEMPTS
            # -------------------------------------------------

            attempts = (
                UserExam.objects
                .filter(
                    user=request.user,
                    exam=exam,
                    submitted_at__isnull=False,
                )
                .count()
            )

            if (
                lesson.quiz_max_attempts
                and attempts >= lesson.quiz_max_attempts
            ):

                messages.error(
                    request,
                    (
                        "You have reached the maximum "
                        f"attempts ({lesson.quiz_max_attempts}) "
                        "for this lesson."
                    ),
                )

                return redirect(
                    "courses:course_learn_lesson",
                    slug=course_slug,
                    lesson_id=lesson.id,
                )

            # -------------------------------------------------
            # STORE COURSE CONTEXT
            # -------------------------------------------------

            request.session[
                "course_exam_context"
            ] = {
                "course_slug": course_slug,
                "lesson_id": lesson.id,
            }

    # =========================================================
    # ACCESS CHECK
    # =========================================================

    allowed, reason = can_access_exam(
        request.user,
        exam,
    )

    if not allowed:

        logger.info(
            "Exam access denied | "
            "user=%s | exam=%s | reason=%s",
            request.user.id,
            exam.id,
            reason,
        )

        if reason == "Prerequisite exam required":
            messages.info(
                request,
                "Complete the prerequisite exam first.",
            )
        elif exam.is_free:
            messages.info(
                request,
                "This free exam is currently unavailable.",
            )
        else:
            messages.info(
                request,
                (
                    "This exam is premium. "
                    "Please subscribe to unlock access."
                ),
            )

        locked_url = reverse(
            "quiz:exam_locked",
            args=[exam.id],
        )
        if reason:
            locked_url = f"{locked_url}?{urlencode({'reason': reason})}"

        return redirect(locked_url)

    # =========================================================
    # CREATE / RESUME EXAM ATTEMPT
    # =========================================================

    try:

        with transaction.atomic():

            # -------------------------------------------------
            # LOCK EXISTING ACTIVE ATTEMPT
            # -------------------------------------------------

            existing = (
                UserExam.objects
                .select_for_update()
                .filter(
                    user=request.user,
                    exam=exam,
                    submitted_at__isnull=True,
                )
                .first()
            )

            if existing:

                logger.info(
                    "Resuming existing exam attempt | "
                    "user=%s | exam=%s | user_exam=%s",
                    request.user.id,
                    exam.id,
                    existing.id,
                )

                return redirect(
                    "quiz:exam_take",
                    user_exam_id=existing.id,
                )

            # -------------------------------------------------
            # CREATE USER EXAM FIRST
            # -------------------------------------------------

            ue = UserExam.objects.create(
                user=request.user,
                exam=exam,
            )

            logger.info(
                "Created UserExam | "
                "user=%s | exam=%s | user_exam=%s",
                request.user.id,
                exam.id,
                ue.id,
            )

            # -------------------------------------------------
            # ALLOCATE QUESTIONS
            # -------------------------------------------------

            questions = allocate_questions_for_exam(
                exam,
                seed=ue.id,
            )

            if not questions:

                logger.error(
                    "No questions allocated | "
                    "user=%s | exam=%s | user_exam=%s",
                    request.user.id,
                    exam.id,
                    ue.id,
                )

                raise ValueError(
                    "No questions were allocated for this exam."
                )

            logger.info(
                "Questions allocated | "
                "exam=%s | user_exam=%s | count=%s",
                exam.id,
                ue.id,
                len(questions),
            )

            # -------------------------------------------------
            # STORE QUESTION ORDER
            # -------------------------------------------------

            ue.question_order = [
                question.id
                for question in questions
            ]

            ue.current_index = 0

            ue.save(
                update_fields=[
                    "question_order",
                    "current_index",
                ]
            )

            # -------------------------------------------------
            # CREATE USER ANSWERS
            # -------------------------------------------------

            UserAnswer.objects.bulk_create(
                [
                    UserAnswer(
                        user_exam=ue,
                        question=question,
                    )
                    for question in questions
                ]
            )

            logger.info(
                "UserAnswer records created | "
                "user_exam=%s | count=%s",
                ue.id,
                len(questions),
            )

    except Exception:

        # Keep technical details in the server log only.
        # Never expose the exception to the student.

        logger.exception(
            "EXAM START FAILED | user=%s | exam=%s",
            request.user.id,
            exam.id,
        )

        messages.error(
            request,
            "This exam is not properly configured. Please contact support.",
        )

        return redirect(
            "quiz:student_dashboard"
        )

    # =========================================================
    # GO TO FIRST QUESTION
    # =========================================================

    logger.info(
        "Starting exam questions | "
        "user=%s | exam=%s | user_exam=%s",
        request.user.id,
        exam.id,
        ue.id,
    )

    return redirect(
        "quiz:exam_question",
        user_exam_id=ue.id,
        index=0,
    )



@login_required
def exam_take(request, user_exam_id):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Take page memory usage: {mem} MB")
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)
    return redirect('quiz:exam_question', user_exam_id=ue.id, index=ue.current_index or 0)


@login_required
def exam_question(request, user_exam_id, index):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Question page memory usage: {mem} MB")

    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    remaining = ue.time_remaining()
    if remaining <= 0:
       from quiz.services.grading import grade_exam
       is_mock = request.session.get(f"mock_exam_{ue.id}", False)
       grade_exam(ue, None, is_mock=is_mock)
       return redirect('quiz:student_dashboard')

    q_ids = ue.question_order or []

    if index < 0 or index >= len(q_ids):
        return redirect('quiz:exam_take', user_exam_id=ue.id)

    q_id = q_ids[index]
    ua = ue.answers.get(question_id=q_id)
    q = ua.question

    # -------------------------------
    # ✅ SAVE ANSWER (POST HANDLING)
    # -------------------------------
    if request.method == "POST":

        # SINGLE / TF / DROPDOWN
        if q.question_type in ['single', 'tf', 'dropdown']:
            choice_id = request.POST.get(f"question_{q.id}")
            if choice_id:
                ua.choice_id = int(choice_id)
            else:
                ua.choice = None
            ua.selections = None
            ua.raw_answer = None

        # MULTI
        elif q.question_type == 'multi':
            selected = request.POST.getlist(f"question_{q.id}")
            ua.selections = [int(x) for x in selected] if selected else []
            ua.choice = None
            ua.raw_answer = None

        # TEXT BASED
        elif q.question_type in ['fill', 'numeric', 'order']:
            ua.raw_answer = request.POST.get(f"question_{q.id}", "").strip()
            ua.choice = None
            ua.selections = None

        ua.save()

        nav = request.POST.get("nav")

        if nav == "next":
            return redirect('quiz:exam_question', ue.id, index + 1)

        elif nav == "prev":
            return redirect('quiz:exam_question', ue.id, index - 1)

        elif nav == "review":
            return redirect('quiz:exam_review', ue.id)

    # -------------------------------
    # DISPLAY QUESTION
    # -------------------------------

    choices = list(q.choices.all()) if q.question_type in ('single', 'multi', 'tf', 'dropdown') else []
    if choices:
        random.Random(f"{ue.id}:{q.id}").shuffle(choices)

    ue.current_index = index
    ue.save()

    progress = int(((index + 1) / len(q_ids)) * 100) if q_ids else 0

    return render(request, 'quiz/student/exam/exam_question.html', {
        'user_exam': ue,
        'ua': ua,
        'question': q,
        'choices': choices,
        'index': index,
        'total': len(q_ids),
        'remaining': remaining,
        'progress': progress,
    })


@login_required
def autosave(request, user_exam_id):
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # refuse autosave after submit
    if ue.submitted_at:
        return JsonResponse(
            {"status": "attempt_already_submitted"},
            status=409
        )

    if request.method != "POST":
        return JsonResponse(
            {"status": "method_not_allowed"},
            status=405
        )

    autosave_answers(ue, request.POST)

    return JsonResponse({"status": "ok"})




@login_required
def exam_submit(request, user_exam_id):

    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    is_mock = request.session.get(f"mock_exam_{ue.id}", False)

    if request.method == "POST":
        grade_exam(ue, request.POST, is_mock=is_mock)
    else:
        grade_exam(ue, None, is_mock=is_mock)

    return redirect('quiz:exam_result', user_exam_id=ue.id)




@login_required
def exam_result(request, user_exam_id):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Result page memory usage: {mem} MB")
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # =====================================================
    # 🎓 COURSE CONTEXT (if exam launched from course)
    # =====================================================
    course_context = request.session.get("course_exam_context")
    next_lesson = None

    if course_context:
        from courses.services.quiz_completion import handle_course_quiz_completion
        from courses.models import Lesson
        from courses.services.progress import get_next_lesson
        from courses.models import Course

        # Run completion logic ONLY ONCE
        if not request.session.get(f"course_exam_handled_{ue.id}"):
            handle_course_quiz_completion(
                request=request,
                user_exam=ue,
                context=course_context
            )
            request.session[f"course_exam_handled_{ue.id}"] = True

        # Resolve next lesson
        try:
            course = Course.objects.get(slug=course_context["course_slug"])
            current_lesson = Lesson.objects.get(
                id=course_context["lesson_id"],
                section__course=course
            )
            next_lesson = get_next_lesson(course, current_lesson)
        except Exception:
            next_lesson = None

    # =====================================================
    # 🧪 MOCK DETECTION
    # =====================================================
    is_mock = ue.passed is None

    # =====================================================
    # HANDLE FEEDBACK SUBMISSION
    # =====================================================
    if request.method == 'POST':
        qid_raw = request.POST.get('question_id')
        comment = (request.POST.get('comment') or '').strip()
        is_incorrect = bool(request.POST.get('is_answer_incorrect'))

        try:
            qid = int(qid_raw)
        except (TypeError, ValueError):
            messages.error(request, "Invalid question reference.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        if not ue.answers.filter(question_id=qid).exists():
            messages.error(request, "This question does not belong to your exam.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        if not comment and not is_incorrect:
            messages.info(request, "Please enter a comment or mark incorrect.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        if QuestionFeedback.objects.filter(
            user=request.user,
            user_exam=ue,
            question_id=qid
        ).exists():
            messages.info(request, "Feedback already submitted.")
            return redirect('quiz:exam_result', user_exam_id=ue.id)

        QuestionFeedback.objects.create(
            user=request.user,
            user_exam=ue,
            question_id=qid,
            comment=comment,
            is_answer_incorrect=is_incorrect,
        )

        messages.success(request, "Thank you for your feedback!")
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    # =====================================================
    # LOAD ANSWERS
    # =====================================================
    answers = list(
        ue.answers
        .select_related('question', 'choice')
        .prefetch_related('question__choices')
    )

    # =====================================================
    # BUILD ANSWER DISPLAY DATA
    # =====================================================
    for ans in answers:
        q = ans.question
        ans.user_answers_display = []
        ans.correct_answers_display = []

        if q.question_type in ('single', 'dropdown', 'tf'):
            if ans.choice:
                ans.user_answers_display = [ans.choice.text]
            correct = q.choices.filter(is_correct=True).first()
            if correct:
                ans.correct_answers_display = [correct.text]

        elif q.question_type == 'multi':
            selected_ids = set(ans.selections or [])
            correct_ids = set(
                q.choices.filter(is_correct=True)
                .values_list('id', flat=True)
            )

            ans.user_answers_display = list(
                q.choices.filter(id__in=selected_ids)
                .values_list('text', flat=True)
            )
            ans.correct_answers_display = list(
                q.choices.filter(is_correct=True)
                .values_list('text', flat=True)
            )

            if selected_ids == correct_ids:
                ans.is_correct = True
            elif selected_ids & correct_ids:
                ans.is_correct = None
            else:
                ans.is_correct = False

        elif q.question_type == 'fill':
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]
            if q.answer_text:
                ans.correct_answers_display = [q.answer_text]

        elif q.question_type == 'numeric':
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]
            if q.answer_numeric is not None:
                ans.correct_answers_display = [str(q.answer_numeric)]

        elif q.question_type == 'order':
            if ans.selections:
                choice_map = {
                    str(c.id): c.text
                    for c in q.choices.all()
                }
                ans.user_answers_display = [
                    choice_map.get(str(cid), str(cid))
                    for cid in ans.selections
                ]
            correct_order = list(
                q.choices.order_by('order_index')
                .values_list('text', flat=True)
            )
            ans.correct_answers_display = correct_order

    return render(request, 'quiz/student/exam/exam_result.html', {
        'user_exam': ue,
        'answers': answers,
        'next_lesson': next_lesson,
        'is_mock': is_mock,
    })
