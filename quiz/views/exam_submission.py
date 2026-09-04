from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from quiz.models import UserExam
from quiz.services.grading import grade_exam


@login_required
@require_POST
def exam_submit_dashboard(request, user_exam_id):
    """Grade a submitted attempt and return the student to their dashboard."""
    user_exam = get_object_or_404(
        UserExam,
        pk=user_exam_id,
        user=request.user,
    )

    if user_exam.submitted_at:
        return redirect("quiz:student_dashboard")

    is_mock = request.session.get(f"mock_exam_{user_exam.id}", False)
    grade_exam(user_exam, request.POST, is_mock=is_mock)

    course_context = request.session.get("course_exam_context")
    if course_context and not request.session.get(f"course_exam_handled_{user_exam.id}"):
        from courses.services.quiz_completion import handle_course_quiz_completion

        handle_course_quiz_completion(
            request=request,
            user_exam=user_exam,
            context=course_context,
        )
        request.session[f"course_exam_handled_{user_exam.id}"] = True

    return redirect("quiz:student_dashboard")
