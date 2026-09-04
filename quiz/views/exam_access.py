from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from quiz.models import Exam


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
