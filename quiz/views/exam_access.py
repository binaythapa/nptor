from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import Exam, UserExam
from quiz.services.grading import grade_exam


@login_required
def exam_locked(request, exam_id):
    """Render the access-required page for an exam the student cannot start."""
    exam = get_object_or_404(
        Exam,
        pk=exam_id,
        is_published=True,
    )

    return render(
        request,
        "quiz/student/exam/exam_locked.html",
        {
            "exam": exam,
            "reason": request.GET.get("reason", ""),
        },
    )


@login_required
def exam_expired(request, user_exam_id):
    """Finalize an expired attempt and display its expiry confirmation page."""
    user_exam = get_object_or_404(
        UserExam,
        pk=user_exam_id,
        user=request.user,
    )

    if not user_exam.submitted_at:
        is_mock = request.session.get(f"mock_exam_{user_exam.id}", False)
        grade_exam(user_exam, None, is_mock=is_mock)

    return render(
        request,
        "quiz/student/exam/exam_expired.html",
        {"user_exam": user_exam},
    )
