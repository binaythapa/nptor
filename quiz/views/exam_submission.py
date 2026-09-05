from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from quiz.models import UserExam
from quiz.services.grading import grade_exam


def _finish_course_quiz_if_needed(request, user_exam):
    course_context = request.session.get("course_exam_context")
    if not course_context or request.session.get(f"course_exam_handled_{user_exam.id}"):
        return

    from courses.services.quiz_completion import handle_course_quiz_completion

    handle_course_quiz_completion(
        request=request,
        user_exam=user_exam,
        context=course_context,
    )
    request.session[f"course_exam_handled_{user_exam.id}"] = True


def _course_quiz_return_redirect(request):
    """Return the course lesson redirect when this attempt came from a course."""
    course_context = request.session.get("course_exam_context")
    if not course_context:
        return None

    course_slug = course_context.get("course_slug")
    lesson_id = course_context.get("lesson_id")
    if not course_slug or not lesson_id:
        return None

    return redirect(
        "courses:course_learn_lesson",
        slug=course_slug,
        lesson_id=lesson_id,
    )


@login_required
def exam_submit_dashboard(request, user_exam_id):
    """Finalize an exam safely for both timer expiry and explicit submit."""
    user_exam = get_object_or_404(
        UserExam,
        pk=user_exam_id,
        user=request.user,
    )

    # A direct browser visit/refresh while the attempt is active must never
    # submit it. If the server confirms expiry, finalize the answers already
    # persisted in UserAnswer as the timer-expiry fallback.
    if request.method == "GET":
        if not user_exam.submitted_at and user_exam.time_remaining() <= 0:
            is_mock = request.session.get(f"mock_exam_{user_exam.id}", False)
            grade_exam(user_exam, None, is_mock=is_mock)
            _finish_course_quiz_if_needed(request, user_exam)

            course_redirect = _course_quiz_return_redirect(request)
            if course_redirect:
                return course_redirect

        return redirect("quiz:student_dashboard")

    if request.method != "POST":
        return redirect("quiz:student_dashboard")

    # POST is the explicit final submission. The grading service persists the
    # submitted answers, score, pass/fail state, and submitted timestamp.
    if user_exam.submitted_at:
        course_redirect = _course_quiz_return_redirect(request)
        if course_redirect:
            return course_redirect
        return redirect("quiz:exam_result", user_exam_id=user_exam.id)

    is_mock = request.session.get(f"mock_exam_{user_exam.id}", False)
    grade_exam(user_exam, request.POST, is_mock=is_mock)
    _finish_course_quiz_if_needed(request, user_exam)

    course_redirect = _course_quiz_return_redirect(request)
    if course_redirect:
        return course_redirect

    return redirect("quiz:exam_result", user_exam_id=user_exam.id)
