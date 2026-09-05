from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import Exam, ExamTrack, Question


PREVIEW_QUESTION_COUNT = 3


@login_required
def exam_preview(request, exam_id):
    exam = get_object_or_404(
        Exam.objects.select_related("primary_category", "primary_category__domain"),
        pk=exam_id,
        is_published=True,
    )

    track_slug = request.GET.get("track")
    if not track_slug:
        return redirect("quiz:exam_list")

    track = get_object_or_404(
        ExamTrack,
        slug=track_slug,
        is_active=True,
        organization__isnull=True,
    )
    if not track.track_exams.filter(exam=exam).exists():
        return redirect("quiz:exam_list")

    category = exam.primary_category
    questions = Question.objects.filter(
        is_active=True,
        is_deleted=False,
        organization__isnull=True,
    )
    if category:
        questions = questions.filter(primary_category=category)
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
            "track": track,
        },
    )
