import math
import random
import logging

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

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
from django.urls import reverse_lazy
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

        messages.info(
            request,
            (
                "This exam is premium. "
                "Please subscribe to unlock access."
            ),
        )

        return redirect(
            "quiz:exam_locked",
            exam_id=exam.id,
        )

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
       return redirect('quiz:exam_submit', user_exam_id=ue.id)

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
        random.shuffle(choices)

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
            if q.correct_text:
                ans.correct_answers_display = [q.correct_text]

        elif q.question_type == 'numeric':
            if ans.raw_answer:
                ans.user_answers_display = [ans.raw_answer]
            if q.numeric_answer is not None:
                ans.correct_answers_display = [str(q.numeric_answer)]

    # =====================================================
    # ACCURACY / BEST SCORE
    # =====================================================
    total = len(answers)
    correct_count = sum(1 for a in answers if a.is_correct is True)
    accuracy = round((correct_count / total) * 100, 2) if total else 0

    best_score = (
        UserExam.objects
        .filter(
            user=request.user,
            exam=ue.exam,
            submitted_at__isnull=False,
            passed__isnull=False
        )
        .order_by('-score')
        .values_list('score', flat=True)
        .first()
    ) or ue.score

    # =====================================================
    # RETAKE COOLDOWN
    # =====================================================
    cooldown_minutes = getattr(settings, "RETAKE_COOLDOWN_MINUTES", 0)
    cooldown_seconds = 0
    can_retake = True

    if not is_mock and cooldown_minutes and ue.submitted_at:
        elapsed = (timezone.now() - ue.submitted_at).total_seconds()
        remaining = max(0, (cooldown_minutes * 60) - elapsed)
        if remaining > 0:
            can_retake = False
            cooldown_seconds = int(remaining)

    # =====================================================
    # FEEDBACK MAPS
    # =====================================================
    feedback_qs = QuestionFeedback.objects.filter(
        user=request.user,
        user_exam=ue
    )
    feedback_map = {fb.question_id: fb for fb in feedback_qs}

    for ans in answers:
        ans.has_feedback = ans.question_id in feedback_map

    other_feedback_qs = (
        QuestionFeedback.objects
        .filter(question_id__in=[a.question_id for a in answers])
        .exclude(user=request.user)
        .select_related('user')
        .order_by('-created_at')
    )

    comments_map = {}
    for fb in other_feedback_qs:
        comments_map.setdefault(fb.question_id, []).append(fb)

    from pages.models import Testimonial

    '''
    # =====================================================
    # ⭐ TESTIMONIAL POPUP LOGIC
    # =====================================================
    

    show_testimonial_popup = False

    if ue.passed and not is_mock:

        # Check if already submitted testimonial for this track
        existing = Testimonial.objects.filter(
            user=request.user,
            exam_track=ue.exam.track
        ).exists()

        if not existing:
            show_testimonial_popup = True
    

    show_testimonial_popup = False
    testimonial_exam_track = None
    testimonial_course = None
    testimonial_study_plan = None

    if ue.passed and not is_mock and ue.exam.track:

        existing = Testimonial.objects.filter(
            user=request.user,
            exam_track=ue.exam.track
        ).exists()

        if not existing:
            show_testimonial_popup = True
            testimonial_exam_track = ue.exam.track
    print("DEBUG → PASSED:", ue.passed)
    print("DEBUG → IS MOCK:", is_mock)
    print("DEBUG → TRACK:", ue.exam.track)
    print("DEBUG → SHOW POPUP:", show_testimonial_popup)

    existing_qs = Testimonial.objects.filter(
        user=request.user,
        exam_track=ue.exam.track
    )

    print("DEBUG → EXISTING COUNT:", existing_qs.count())
    '''

    from pages.services.testimonials import get_testimonial_context

    testimonial_context = get_testimonial_context(
        request.user,
        exam_track=ue.exam.track,
        trigger=(ue.passed and not is_mock)
    )
    # =====================================================
    # RENDER
    # =====================================================
    return render(
        request,
        'quiz/student/exam/result.html',
        {
            'user_exam': ue,
            'answers': answers,
            'accuracy': accuracy,
            'best_score': best_score,
            'can_retake': can_retake,
            'cooldown_seconds': cooldown_seconds,
            'feedback_map': feedback_map,
            'comments_map': comments_map,
            'is_mock': is_mock,

            # 🎓 COURSE AWARE
            'course_context': course_context,
            'next_lesson': next_lesson,

            # Testimonial
            #'show_testimonial_popup': show_testimonial_popup,
            **testimonial_context,
        }
    )





@login_required
def exam_expired(request, user_exam_id):
    return redirect('quiz:exam_submit', user_exam_id=user_exam_id)




@login_required
def exam_resume(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    # 🔐 Subscription + unlock check
    allowed, reason = can_access_exam(request.user, exam)
    if not allowed:
        messages.error(request, reason)
        return redirect('quiz:exam_locked', exam_id=exam.id)

    active = UserExam.objects.filter(
        user=request.user,
        exam=exam,
        submitted_at__isnull=True
    ).order_by('-started_at').first()

    if active:
        return redirect('quiz:exam_take', user_exam_id=active.id)

    return redirect('quiz:exam_start', exam_id=exam.id)










@login_required
@require_POST
def start_trial(request, track_id):
    """
    Activate the 7-day free trial for an exam track.

    New subscription architecture:

        User
          ↓
        Subscription
          ↓
        SubscriptionEntitlement
          ↓
        ResourceAccess

    No legacy ExamTrackSubscription is used.
    """

    track = get_object_or_404(
        ExamTrack,
        id=track_id,
    )

    # =========================================================
    # TRIAL PLAN
    # =========================================================

    plan = get_object_or_404(
        SubscriptionPlan,
        code="free-trial-7-day",
        is_active=True,
    )

    # =========================================================
    # PREVENT DUPLICATE TRIAL
    # =========================================================
    #
    # Check whether this user already has an entitlement
    # for this track under the trial plan.
    #
    # We intentionally check historical subscriptions as well,
    # because the trial should only be usable once.
    # =========================================================

    trial_used = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=request.user,
            subscription__plan=plan,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
            track=track,
        )
        .exists()
    )

    if trial_used:
        messages.error(
            request,
            "Trial already used.",
        )
        return redirect("quiz:exam_list")

    # =========================================================
    # CREATE SUBSCRIPTION + ENTITLEMENT
    # =========================================================

    try:
        with transaction.atomic():

            subscription, entitlement = (
                SubscriptionService
                .create_or_reactivate_subscription(
                    user=request.user,
                    resource_type=(
                        SubscriptionEntitlement.RESOURCE_TRACK
                    ),
                    resource=track,
                    plan=plan,
                    granted_by=None,
                    notes="7-day free trial",
                )
            )

            # =================================================
            # RESOURCE ACCESS
            # =================================================
            #
            # SubscriptionEntitlement is the entitlement
            # definition. ResourceAccess is the actual access.
            # =================================================

            AccessService.grant_access(
                user=request.user,
                resource_type=(
                    SubscriptionEntitlement.RESOURCE_TRACK
                ),
                resource=track,
                source=ResourceAccess.SOURCE_ADMIN,
                subscription=subscription,
                expires_at=subscription.expires_at,
            )

    except Exception:
        logger.exception(
            "Failed to activate 7-day trial for user=%s track=%s",
            request.user.id,
            track.id,
        )

        messages.error(
            request,
            "Unable to activate the trial. Please try again.",
        )

        return redirect("quiz:exam_list")

    messages.success(
        request,
        "7-day free trial activated!",
    )

    return redirect(
        "quiz:student_dashboard"
    )












    # =========================================================
    # SELECTION STATE
    # =========================================================

    selected_qs = []

    selected_ids = set()

    remaining_needed = total_needed

    # =========================================================
    # HELPER: CATEGORY QUESTION POOL
    # =========================================================

    def get_category_pool(category):

        if not category:
            return []

        try:

            category_ids = (
                category
                .get_descendants_include_self()
            )

        except Exception:

            category_ids = [category.id]

        return list(
            base_qs.filter(
                models.Q(
                    primary_category_id__in=category_ids
                )
                |
                models.Q(
                    categories__id__in=category_ids
                )
            )
            .exclude(
                id__in=selected_ids
            )
            .distinct()
            .order_by()
        )

    # =========================================================
    # 1. FIXED ALLOCATIONS
    # =========================================================

    percentage_allocations = []

    percentage_sum = 0

    fixed_total = sum(
        allocation.fixed_count or 0
        for allocation in allocations
    )

    if fixed_total > total_needed:

        raise ValueError(
            (
                f"Fixed allocation ({fixed_total}) "
                f"exceeds exam.question_count "
                f"({total_needed})."
            )
        )

    for allocation in allocations:

        if allocation.fixed_count is not None:

            if remaining_needed <= 0:
                break

            pool = get_category_pool(
                allocation.category
            )

            rng.shuffle(pool)

            take = min(
                len(pool),
                allocation.fixed_count,
                remaining_needed,
            )

            chosen = pool[:take]

            selected_qs.extend(
                chosen
            )

            selected_ids.update(
                q.id
                for q in chosen
            )

            remaining_needed -= take

        elif allocation.percentage is not None:

            percentage_allocations.append(
                allocation
            )

            percentage_sum += (
                allocation.percentage
            )

    # =========================================================
    # 2. PERCENTAGE ALLOCATIONS
    # =========================================================

    if (
        percentage_allocations
        and remaining_needed > 0
        and percentage_sum > 0
    ):

        raw_allocations = []

        for allocation in percentage_allocations:

            scaled = (
                allocation.percentage
                / percentage_sum
            ) * remaining_needed

            floor_count = math.floor(
                scaled
            )

            remainder = (
                scaled - floor_count
            )

            raw_allocations.append(
                (
                    allocation,
                    floor_count,
                    remainder,
                )
            )

        percentage_counts = {
            allocation.id: count
            for allocation, count, _ in raw_allocations
        }

        allocated = sum(
            percentage_counts.values()
        )

        leftover = (
            remaining_needed
            - allocated
        )

        # -----------------------------------------------------
        # Largest remainder method
        # -----------------------------------------------------

        for (
            allocation,
            _,
            remainder,
        ) in sorted(
            raw_allocations,
            key=lambda item: item[2],
            reverse=True,
        ):

            if leftover <= 0:
                break

            percentage_counts[
                allocation.id
            ] += 1

            leftover -= 1

        # -----------------------------------------------------
        # Select questions
        # -----------------------------------------------------

        for allocation in percentage_allocations:

            count = percentage_counts.get(
                allocation.id,
                0,
            )

            if count <= 0:
                continue

            if remaining_needed <= 0:
                break

            pool = get_category_pool(
                allocation.category
            )

            rng.shuffle(pool)

            take = min(
                len(pool),
                count,
                remaining_needed,
            )

            chosen = pool[:take]

            selected_qs.extend(
                chosen
            )

            selected_ids.update(
                q.id
                for q in chosen
            )

            remaining_needed -= take

    # =========================================================
    # 3. PRIMARY CATEGORY FALLBACK
    # =========================================================

    if (
        remaining_needed > 0
        and exam.primary_category_id
    ):

        pool = get_category_pool(
            exam.primary_category
        )

        rng.shuffle(pool)

        chosen = pool[
            :remaining_needed
        ]

        selected_qs.extend(
            chosen
        )

        selected_ids.update(
            q.id
            for q in chosen
        )

        remaining_needed -= len(
            chosen
        )

    # =========================================================
    # 4. EXAM MULTI-CATEGORY FALLBACK
    # =========================================================

    if remaining_needed > 0:

        category_ids = set()

        for category in exam.categories.all():

            try:

                category_ids.update(
                    category
                    .get_descendants_include_self()
                )

            except Exception:

                category_ids.add(
                    category.id
                )

        if category_ids:

            pool = list(
                base_qs.filter(
                    models.Q(
                        primary_category_id__in=category_ids
                    )
                    |
                    models.Q(
                        categories__id__in=category_ids
                    )
                )
                .exclude(
                    id__in=selected_ids
                )
                .distinct()
                .order_by()
            )

            rng.shuffle(pool)

            chosen = pool[
                :remaining_needed
            ]

            selected_qs.extend(
                chosen
            )

            selected_ids.update(
                q.id
                for q in chosen
            )

            remaining_needed -= len(
                chosen
            )

    # =========================================================
    # 5. FINAL TENANT-SAFE FALLBACK
    # =========================================================

    if remaining_needed > 0:

        pool = list(
            base_qs
            .exclude(
                id__in=selected_ids
            )
            .order_by()
        )

        rng.shuffle(pool)

        chosen = pool[
            :remaining_needed
        ]

        selected_qs.extend(
            chosen
        )

        selected_ids.update(
            q.id
            for q in chosen
        )

    # =========================================================
    # FINAL SHUFFLE
    # =========================================================

    rng.shuffle(
        selected_qs
    )

    return selected_qs[
        :total_needed
    ]























@login_required
def exam_locked(request, exam_id):
    """
    Shown when user tries to access a locked exam.
    Displays reason instead of silent redirect.
    """
    exam = get_object_or_404(Exam, pk=exam_id)

    reasons = []

    # Prerequisite exams
    prereqs = exam.prerequisite_exams.all()
    if prereqs.exists():
        missing = [
            p.title for p in prereqs
            if not UserExam.objects.filter(
                user=request.user,
                exam=p,
                passed=True
            ).exists()
        ]
        if missing:
            reasons.append(
                "You must pass the following exam(s): " + ", ".join(missing)
            )

    # Level-based lock
    if exam.level and exam.level > 1:
        has_prev_level = UserExam.objects.filter(
            user=request.user,
            exam__level=exam.level - 1,
            passed=True
        ).exists()
        if not has_prev_level:
            reasons.append(
                f"You must pass at least one Level {exam.level - 1} exam."
            )

    return render(request, "quiz/student/exam/exam_locked.html", {
        "exam": exam,
        "reasons": reasons or ["This exam is currently locked."],
    })





@login_required
def mock_exam_start(request, exam_id):
    """
    Starts a mock exam:
    - Per-exam mock attempt limit
    - No prerequisites
    - No pass/fail impact
    - Does NOT unlock progression
    """

    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    # =====================================================
    # 🔒 PER-EXAM MOCK LIMIT
    # =====================================================
    max_mock = exam.max_mock_attempts or 0

    used_mocks = UserExam.objects.filter(
        user=request.user,
        exam=exam,
        passed__isnull=True,          # 👈 mock attempts
        submitted_at__isnull=False
    ).count()

    if max_mock == 0:
        messages.error(
            request,
            "Mock exams are disabled for this exam."
        )
        return redirect("quiz:student_dashboard")

    if used_mocks >= max_mock:
        messages.error(
            request,
            f"Mock attempt limit reached ({max_mock})."
        )
        return redirect("quiz:student_dashboard")

    # =====================================================
    # CREATE MOCK ATTEMPT
    # =====================================================
    try:
        with transaction.atomic():
            ue = UserExam.objects.create(
                user=request.user,
                exam=exam,
                passed=None      # ✅ Explicit mock marker
            )

            questions = allocate_questions_for_exam(
                exam,
                seed=ue.id       # deterministic
            )

            if not questions:
                raise ValueError("No questions allocated")

            ue.question_order = [q.id for q in questions]
            ue.current_index = 0
            ue.save()

            UserAnswer.objects.bulk_create([
                UserAnswer(
                    user_exam=ue,
                    question=q
                )
                for q in questions
            ])

        # Session marker (optional, safe)
        request.session[f"mock_exam_{ue.id}"] = True

    except Exception:
        messages.error(
            request,
            "Mock exam is not available at the moment."
        )
        return redirect("quiz:student_dashboard")

    return redirect(
        "quiz:exam_question",
        user_exam_id=ue.id,
        index=0
    )



@login_required
def exam_review(request, user_exam_id):
   

    user_exam = get_object_or_404(
        UserExam.objects.select_related("exam"),
        id=user_exam_id,
        user=request.user
    )

    remaining = user_exam.time_remaining()

    # Prevent access after submission
    if user_exam.submitted_at:
        return redirect("quiz:exam_result", user_exam.id)

    # Expiration check
    if user_exam.exam.duration_seconds:
        expiry_time = user_exam.started_at + timedelta(
            seconds=user_exam.exam.duration_seconds
        )
        if timezone.now() > expiry_time:
            return redirect("quiz:exam_expired", user_exam.id)

    question_ids = user_exam.question_order or []
    if not question_ids:
        return redirect("quiz:exam_question", user_exam.id, 0)

    # Fetch questions with choices
    questions = (
        Question.objects
        .filter(id__in=question_ids)
        .prefetch_related("choices")
    )

    # Preserve order
    question_map = {q.id: q for q in questions}
    ordered_questions = [
        question_map[qid]
        for qid in question_ids
        if qid in question_map
    ]

    # Fetch answers
    user_answers = {
        ua.question_id: ua
        for ua in user_exam.answers.all()
    }

    answered_count = 0

    for q in ordered_questions:
        ua = user_answers.get(q.id)

        if not ua:
            continue

        if q.question_type in ["single", "tf", "dropdown"]:
            if ua.choice:
                answered_count += 1

        elif q.question_type == "multi":
            if ua.selections and len(ua.selections) > 0:
                answered_count += 1

        elif q.question_type in ["fill", "numeric", "order"]:
            if ua.raw_answer and ua.raw_answer.strip():
                answered_count += 1

        elif q.question_type == "match":
            if ua.selections and len(ua.selections) > 0:
                answered_count += 1

    total = len(ordered_questions)
    unanswered_count = total - answered_count

    return render(request, "quiz/student/exam/exam_review.html", {
        "user_exam": user_exam,
        "questions": ordered_questions,
        "user_answers": user_answers,
        "answered_count": answered_count,
        "unanswered_count": unanswered_count,
        "total_questions": total,
        "remaining": remaining,  # ✅ ADD THIS
    })