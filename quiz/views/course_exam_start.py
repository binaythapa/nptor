from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from courses.models import Course, Lesson
from quiz.models import Exam, UserExam, UserAnswer
from quiz.services.exam_question_allocator import allocate_questions_for_exam
from quiz.services.access import can_access_exam
from subscriptions.services import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def _course_access_allows_quiz(user, course):
    """Return True when the user is allowed to take a quiz from this course."""
    plan = get_plan_for_course(course, None)

    # Free/public courses do not require a separate course entitlement.
    if plan is None or plan.price <= 0:
        return True

    return AccessService.has_access(
        student=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )


@login_required
def course_exam_start(request, exam_id):
    """
    Start an exam launched from a course lesson.

    Course access is the source of authorization for a course quiz.
    The normal exam access rules are still applied for prerequisites.
    Direct/standalone exam launches continue through the original
    exam_start view.
    """
    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    # No course context: let the normal exam launcher handle it.
    if not course_slug or not lesson_id:
        from quiz.views.exams import exam_start as standard_exam_start
        return standard_exam_start(request, exam_id)

    course = get_object_or_404(
        Course,
        slug=course_slug,
        approval_status=Course.APPROVAL_APPROVED,
        is_published=True,
        is_public=True,
    )

    lesson = get_object_or_404(
        Lesson,
        id=lesson_id,
        section__course=course,
        lesson_type=Lesson.TYPE_QUIZ,
        exam_id=exam_id,
    )

    if not _course_access_allows_quiz(request.user, course):
        messages.info(request, "You do not have access to this course.")
        return redirect("courses:course_detail", slug=course.slug)

    # Preserve the existing prerequisite rules.  A course entitlement
    # should grant access to the course quiz, but must not bypass an
    # explicitly configured prerequisite exam.
    allowed, reason = can_access_exam(request.user, lesson.exam)
    if not allowed and reason != "Subscription required":
        messages.info(request, reason or "This exam is currently unavailable.")
        locked_url = reverse("quiz:exam_locked", args=[lesson.exam.id])
        if reason:
            from urllib.parse import urlencode
            locked_url = f"{locked_url}?{urlencode({'reason': reason})}"
        return redirect(locked_url)

    attempts = UserExam.objects.filter(
        user=request.user,
        exam=lesson.exam,
        submitted_at__isnull=False,
    ).count()

    if lesson.quiz_max_attempts and attempts >= lesson.quiz_max_attempts:
        messages.error(
            request,
            f"You have reached the maximum attempts ({lesson.quiz_max_attempts}) for this lesson.",
        )
        return redirect(
            "courses:course_learn_lesson",
            slug=course.slug,
            lesson_id=lesson.id,
        )

    request.session["course_exam_context"] = {
        "course_slug": course.slug,
        "lesson_id": lesson.id,
    }

    exam = lesson.exam

    try:
        with transaction.atomic():
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
                return redirect(
                    "quiz:exam_take",
                    user_exam_id=existing.id,
                )

            ue = UserExam.objects.create(
                user=request.user,
                exam=exam,
            )

            questions = allocate_questions_for_exam(
                exam,
                seed=ue.id,
            )

            if not questions:
                raise ValueError("No questions were allocated for this exam.")

            ue.question_order = [question.id for question in questions]
            ue.current_index = 0
            ue.save(update_fields=["question_order", "current_index"])

            UserAnswer.objects.bulk_create(
                [
                    UserAnswer(
                        user_exam=ue,
                        question=question,
                    )
                    for question in questions
                ]
            )

    except Exception:
        messages.error(
            request,
            "This exam is not properly configured. Please contact support.",
        )
        return redirect("quiz:student_dashboard")

    return redirect(
        "quiz:exam_question",
        user_exam_id=ue.id,
        index=0,
    )
