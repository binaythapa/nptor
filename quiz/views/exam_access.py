from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect

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


@login_required
def exam_review(request, user_exam_id):
    """Display the editable final review page before an exam is submitted."""
    user_exam = get_object_or_404(
        UserExam,
        pk=user_exam_id,
        user=request.user,
    )

    if user_exam.submitted_at:
        return redirect("quiz:exam_result", user_exam_id=user_exam.id)

    remaining = user_exam.time_remaining()
    if remaining <= 0:
        is_mock = request.session.get(f"mock_exam_{user_exam.id}", False)
        grade_exam(user_exam, None, is_mock=is_mock)
        return redirect("quiz:student_dashboard")

    question_ids = user_exam.question_order or []
    answers = (
        user_exam.answers
        .select_related("question", "choice")
        .prefetch_related("question__choices")
    )
    answer_map = {answer.question_id: answer for answer in answers}
    questions_by_id = {
        question.id: question
        for question in user_exam.answers.select_related("question").values_list("question", flat=True)
    }

    # Resolve questions in the exact attempt order stored on UserExam.
    questions = []
    for question_id in question_ids:
        answer = answer_map.get(question_id)
        if answer:
            questions.append(answer.question)

    def is_answered(answer):
        if not answer:
            return False
        question_type = answer.question.question_type
        if question_type in ("single", "tf", "dropdown"):
            return answer.choice_id is not None
        if question_type in ("multi", "match", "order"):
            return bool(answer.selections)
        if question_type in ("fill", "numeric"):
            return bool((answer.raw_answer or "").strip())
        return bool(answer.choice_id or answer.selections or (answer.raw_answer or "").strip())

    answered_count = sum(
        1 for question_id in question_ids if is_answered(answer_map.get(question_id))
    )
    total_questions = len(question_ids)

    return render(
        request,
        "quiz/student/exam/exam_review.html",
        {
            "user_exam": user_exam,
            "questions": questions,
            "user_answers": answer_map,
            "total_questions": total_questions,
            "answered_count": answered_count,
            "unanswered_count": total_questions - answered_count,
            "remaining": remaining,
        },
    )
