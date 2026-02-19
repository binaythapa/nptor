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
from courses.models import Course, Lesson
from courses.services.progress import get_next_lesson
from courses.services.quiz_completion import *
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
from quiz.services.grading import grade_exam
from quiz.services.answer_persistence import autosave_answers




# Re-assign User in case a custom user model is used (overrides the imported User if needed)
User = get_user_model()

import logging
from core.utils.memory import get_memory_usage_mb

logger = logging.getLogger("django")



@login_required
def exam_start(request, exam_id):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Start page memory usage: {mem} MB")
    exam = get_object_or_404(Exam, pk=exam_id, is_published=True)

    # --------------------------------------------------
    # COURSE CONTEXT (optional)
    # --------------------------------------------------
    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    if course_slug and lesson_id:
        from courses.models import Lesson

        lesson = Lesson.objects.filter(
            id=lesson_id,
            lesson_type=Lesson.TYPE_QUIZ,
            exam=exam
        ).first()

        if lesson:
            # ✅ Enforce max attempts ONLY for course quiz
            attempts = UserExam.objects.filter(
                user=request.user,
                exam=exam,
                submitted_at__isnull=False
            ).count()

            if lesson.quiz_max_attempts and attempts >= lesson.quiz_max_attempts:
                messages.error(
                    request,
                    f"You have reached the maximum attempts "
                    f"({lesson.quiz_max_attempts}) for this lesson."
                )
                return redirect(
                    "courses:course_learn_lesson",
                    slug=course_slug,
                    lesson_id=lesson.id
                )

            # Store context for result → lesson completion
            request.session["course_exam_context"] = {
                "course_slug": course_slug,
                "lesson_id": lesson.id,
            }

    # --------------------------------------------------
    # EXISTING ACCESS CHECK (unchanged)
    # --------------------------------------------------
    allowed, reason = can_access_exam(request.user, exam)
    if not allowed:
        messages.info(
            request,
            "This exam is premium. Please subscribe to unlock access."
        )
        return redirect("quiz:exam_locked", exam_id=exam.id)

    try:
        with transaction.atomic():

            # 🔒 Prevent race condition (double attempts)
            existing = (
                UserExam.objects
                .select_for_update()
                .filter(user=request.user, exam=exam, submitted_at__isnull=True)
                .first()
            )
            if existing:
                return redirect('quiz:exam_take', user_exam_id=existing.id)

            # ==================================================
            # Create attempt FIRST (deterministic seed)
            # ==================================================
            ue = UserExam.objects.create(
                user=request.user,
                exam=exam
            )

            questions = allocate_questions_for_exam(exam, seed=ue.id)
            if not questions:
                raise ValueError("No questions allocated")

            ue.question_order = [q.id for q in questions]
            ue.current_index = 0
            ue.save()

            UserAnswer.objects.bulk_create([
                UserAnswer(user_exam=ue, question=q)
                for q in questions
            ])

    except Exception:
        messages.error(
            request,
            "This exam is not properly configured. Please contact support."
        )
        return redirect('quiz:student_dashboard')

    return redirect('quiz:exam_question', user_exam_id=ue.id, index=0)


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
        return redirect('quiz:exam_expired', user_exam_id=ue.id)

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
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Submit page memory usage: {mem} MB")
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    # Prevent double submit
    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    # Time expired
    if ue.time_remaining() <= 0:
        ue.submitted_at = timezone.now()
        ue.score = 0
        ue.passed = False
        ue.save()
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    if request.method != 'POST':
        return redirect(
            'quiz:exam_question',
            user_exam_id=ue.id,
            index=ue.current_index
        )

    # ✅ Correct mock detection
    is_mock = request.session.get(f"mock_exam_{ue.id}", False)

    grade_exam(ue, request.POST, is_mock=is_mock)

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
        }
    )



@login_required
def exam_expired(request, user_exam_id):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Exam Expire page memory usage: {mem} MB")
    """
    Called when exam time expires.
    Safely finalizes attempt if not already submitted.
    """
    ue = get_object_or_404(UserExam, pk=user_exam_id, user=request.user)

    if ue.submitted_at:
        return redirect('quiz:exam_result', user_exam_id=ue.id)

    ue.submitted_at = timezone.now()
    ue.score = ue.score or 0.0
    ue.passed = False
    ue.save()

    return render(request, "quiz/student/exam/exam_expired.html", {
        "user_exam": ue,
    })



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
    track = get_object_or_404(ExamTrack, id=track_id)

    existing = ExamTrackSubscription.objects.filter(
        user=request.user,
        track=track
    ).exists()

    if existing:
        messages.error(request, "Trial already used.")
        return redirect("quiz:exam_list")

    ExamTrackSubscription.objects.create(
        user=request.user,
        track=track,
        is_active=True,
        is_trial=True,
        expires_at=timezone.now() + timedelta(days=7),
        payment_required=False,
        amount=0
    )

    messages.success(request, "7-day free trial activated!")
    return redirect("quiz:student_dashboard")




def allocate_questions_for_exam(exam, seed=None):
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Allocate Question for Exam page memory usage: {mem} MB")
    """
    Enterprise-grade allocation engine.
    - Supports fixed + percentage allocation
    - Deterministic if seed is provided (recommended: user_exam.id)
    - Prevents over-allocation
    - Uses active questions only
    """

    total_needed = int(exam.question_count)
    if total_needed <= 0:
        return []

    rng = random.Random(seed) if seed is not None else random
    allocations = list(exam.allocations.select_related('category').all())

    base_qs = Question.objects.filter(is_active=True,is_deleted=False)

    selected_qs = []
    selected_ids = set()

    # -------------------------------------------------
    # 0️⃣ Guard: fixed_count overflow
    # -------------------------------------------------
    fixed_total = sum(a.fixed_count or 0 for a in allocations)
    if fixed_total > total_needed:
        raise ValueError(
            f"Fixed allocation ({fixed_total}) exceeds exam.question_count ({total_needed})"
        )

    remaining_needed = total_needed

    # -------------------------------------------------
    # 1️⃣ FIXED COUNT ALLOCATION
    # -------------------------------------------------
    percent_allocs = []
    percent_sum = 0

    for a in allocations:
        if a.fixed_count:
            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]

            pool = list(
                base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
            )
            rng.shuffle(pool)

            take = min(len(pool), a.fixed_count)
            chosen = pool[:take]

            selected_qs.extend(chosen)
            selected_ids.update(q.id for q in chosen)
            remaining_needed -= take
        else:
            percent_allocs.append(a)
            percent_sum += a.percentage

    # -------------------------------------------------
    # 2️⃣ PERCENTAGE ALLOCATION
    # -------------------------------------------------
    if percent_allocs and remaining_needed > 0 and percent_sum > 0:
        raw = []
        for a in percent_allocs:
            scaled = (a.percentage / percent_sum) * remaining_needed
            raw.append((a, math.floor(scaled), scaled % 1))

        percent_counts = {a.id: cnt for a, cnt, _ in raw}
        allocated = sum(percent_counts.values())
        left = remaining_needed - allocated

        # distribute remainders
        for a, _, _ in sorted(raw, key=lambda x: x[2], reverse=True):
            if left <= 0:
                break
            percent_counts[a.id] += 1
            left -= 1

        for a in percent_allocs:
            cnt = percent_counts.get(a.id, 0)
            if cnt <= 0:
                continue

            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]

            pool = list(
                base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
            )
            rng.shuffle(pool)

            chosen = pool[:cnt]
            selected_qs.extend(chosen)
            selected_ids.update(q.id for q in chosen)

    # -------------------------------------------------
    # 3️⃣ FALLBACK: legacy category
    # -------------------------------------------------
    if len(selected_qs) < total_needed and exam.category:
        needed = total_needed - len(selected_qs)
        try:
            cat_ids = exam.category.get_descendants_include_self()
        except Exception:
            cat_ids = [exam.category.id]

        pool = list(
            base_qs.filter(category_id__in=cat_ids).exclude(id__in=selected_ids)
        )
        rng.shuffle(pool)
        selected_qs.extend(pool[:needed])
        selected_ids.update(q.id for q in pool[:needed])

    # -------------------------------------------------
    # 4️⃣ GLOBAL FALLBACK
    # -------------------------------------------------
    if len(selected_qs) < total_needed:
        needed = total_needed - len(selected_qs)
        pool = list(base_qs.exclude(id__in=selected_ids))
        rng.shuffle(pool)
        selected_qs.extend(pool[:needed])

    # -------------------------------------------------
    # FINAL SHUFFLE (order is stored anyway)
    # -------------------------------------------------
    rng.shuffle(selected_qs)
    return selected_qs[:total_needed]





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
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta


@login_required
def exam_review(request, user_exam_id):

    user_exam = get_object_or_404(
        UserExam.objects.select_related("exam"),
        id=user_exam_id,
        user=request.user
    )

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
    })
