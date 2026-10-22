from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from courses.models import Lesson
from quiz.models import ExamTrack, UserExam
from quiz.views import exams as exam_views
from quiz.views.exam_access import exam_expired as original_exam_expired, exam_review as original_exam_review
from quiz.views.exam_submission import exam_submit_dashboard as original_exam_submit_dashboard


def _context_is_valid(request, user_exam):
    # Already submitted attempts may always be reviewed or viewed by their owner
    if user_exam.submitted_at:
        return True

    course_context = request.session.get("course_exam_context")
    if course_context:
        if Lesson.objects.filter(
            id=course_context.get("lesson_id"),
            section__course__slug=course_context.get("course_slug"),
            lesson_type=Lesson.TYPE_QUIZ,
            exam_id=user_exam.exam_id,
        ).exists():
            return True

    track_context = request.session.get("track_exam_context")
    if track_context:
        if ExamTrack.objects.filter(
            slug=track_context.get("track_slug"),
            is_active=True,
            organization__isnull=True,
            track_exams__exam_id=user_exam.exam_id,
        ).exists():
            return True

    # Fallback for active attempts resumed from dashboard or direct attempt flow:
    # Check if this exam belongs to an active track or course lesson, and restore context.
    track = ExamTrack.objects.filter(
        track_exams__exam_id=user_exam.exam_id,
        is_active=True,
        organization__isnull=True,
    ).first()
    if track:
        request.session["track_exam_context"] = {
            "track_slug": track.slug,
            "exam_id": user_exam.exam_id,
        }
        return True

    lesson = (
        Lesson.objects.filter(
            lesson_type=Lesson.TYPE_QUIZ,
            exam_id=user_exam.exam_id,
        )
        .select_related("section__course")
        .first()
    )
    if lesson and lesson.section and lesson.section.course:
        request.session["course_exam_context"] = {
            "course_slug": lesson.section.course.slug,
            "lesson_id": lesson.id,
        }
        return True

    # If the user owns this active attempt, allow taking, answering, and submitting it
    if user_exam.user_id == request.user.id:
        return True

    return False


def contextual_exam_view(view):
    @wraps(view)
    @login_required
    def wrapped(request, user_exam_id, *args, **kwargs):
        user_exam = get_object_or_404(
            UserExam,
            pk=user_exam_id,
            user=request.user,
        )
        if not _context_is_valid(request, user_exam):
            messages.info(request, "Open this exam from its course or certification track.")
            return redirect("quiz:exam_list")
        return view(request, user_exam_id, *args, **kwargs)

    return wrapped


@contextual_exam_view
def exam_take(request, user_exam_id):
    return exam_views.exam_take(request, user_exam_id)


@contextual_exam_view
def exam_question(request, user_exam_id, index):
    return exam_views.exam_question(request, user_exam_id, index)


@contextual_exam_view
def autosave(request, user_exam_id):
    return exam_views.autosave(request, user_exam_id)


@contextual_exam_view
def exam_submit(request, user_exam_id):
    return original_exam_submit_dashboard(request, user_exam_id)


@contextual_exam_view
def exam_result(request, user_exam_id):
    return exam_views.exam_result(request, user_exam_id)


@contextual_exam_view
def exam_expired(request, user_exam_id):
    return original_exam_expired(request, user_exam_id)


@contextual_exam_view
def exam_review(request, user_exam_id):
    return original_exam_review(request, user_exam_id)
