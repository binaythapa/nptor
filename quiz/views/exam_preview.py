from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import Exam, Question


PREVIEW_QUESTION_COUNT = 3


@login_required
def exam_preview(request, exam_id):
    exam = get_object_or_404(
        Exam.objects.select_related("primary_category", "primary_category__domain"),
        pk=exam_id,
        is_published=True,
    )

    if exam.is_free:
        return redirect("quiz:exam_start", exam_id=exam.id)

    category = exam.primary_category
    questions = Question.objects.filter(
        is_active=True,
        is_deleted=False,
        organization__isnull=True,
    )
    if category:
        questions = questions.filter(
            primary_category=category
        )
    else:
        questions = questions.none()

    questions = list(
        questions
        .prefetch_related("choices")
        .order_by("id")[:PREVIEW_QUESTION_COUNT]
    )

    return render(
        request,
        "quiz/student/exam/exam_preview.html",
        {
            "exam": exam,
            "questions": questions,
            "preview_limit": PREVIEW_QUESTION_COUNT,
        },
    )
