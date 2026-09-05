from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from courses.models import Course, Lesson
from quiz.models import Exam, ExamTrack, UserExam, UserAnswer
from quiz.services.exam_question_allocator import allocate_questions_for_exam
from quiz.services.access import can_access_exam
from quiz.services.track_progress import build_track_progress
from subscriptions.services import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def _course_access_allows_quiz(user, course):
    """Return True when the user is allowed to take a quiz from this course."""
    plan = get_plan_for_course(course, None)

    if plan is None or plan.price <= 0:
        return True

    return AccessService.has_access(
        student=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )


def _prepare_track_context(request, exam):
    """Validate a track launch and store the approved context in the session."""
    track_slug = request.GET.get("track")
    if not track_slug:
        return False

    track = get_object_or_404(
        ExamTrack.objects.filter(
            slug=track_slug,
            is_active=True,
            organization__isnull=True,
        ),
        slug=track_slug,
    )

    if not track.track_exams.filter(exam=exam).exists():
        messages.info(request, "This exam is not part of the selected track.")
        return False

    has_track_access = track.is_free() or AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
    )
    if not has_track_access:
        messages.info(request, "You do not have access to this track.")
        return False

    progress = build_track_progress(request.user, track)
    item = next(
        (entry for entry in progress["items"] if entry["exam"].id == exam.id),
        None,
    )
    if item is None or not item["is_unlocked"]:
        messages.info(
            request,
            (item or {}).get("lock_reason") or "This exam is currently locked in the track.",
        )
        return False

    request.session["track_exam_context"] = {
        "track_slug": track.slug,
        "exam_id": exam.id,
    }
    return True


@login_required
def course_exam_start(request, exam_id):
    """
    Start an exam launched from a course lesson or certification track.

    A bare exam URL is rejected. Course launches must identify their quiz
    lesson; track launches must identify an active track containing the exam.
    """
    exam = get_object_or_404(
        Exam,
        pk=exam_id,
        is_published=True,
    )

    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    if not course_slug or not lesson_id:
        if not request.GET.get("track"):
            messages.info(request, "Open this exam from its course or certification track.")
            return redirect("quiz:exam_list")

        if not _prepare_track_context(request, exam):
            return redirect("quiz:learning_track", slug=request.GET.get("track"))

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

    try:
        with transaction.atomic():
            existing = (
                UserExam.objects
                .select_for_update()
                .filter(
                    user=request.user,
                    exam=lesson.exam,
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
                exam=lesson.exam,
            )

            questions = allocate_questions_for_exam(
                lesson.exam,
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
