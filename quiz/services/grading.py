from typing import Tuple
from django.utils import timezone

from quiz.models import (
    UserExam,
    UserAnswer,
    Question,
    Choice,
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def normalize_text(s: str) -> str:
    return " ".join((s or "").lower().split())


# --------------------------------------------------
# Grade ONE answer
# --------------------------------------------------

def grade_answer(
    ua: UserAnswer,
    post_data,
) -> float:
    q: Question = ua.question
    score = 0.0

    # -----------------------------
    # SINGLE / DROPDOWN / TRUE-FALSE
    # -----------------------------
    if q.question_type in ("single", "dropdown", "tf"):
        choice_id = post_data.get(f"question_{q.id}")

        if choice_id is None:
            if ua.choice and ua.is_correct:
                return 1.0
            return 0.0

        try:
            ch = Choice.objects.get(pk=int(choice_id), question=q)
            ua.choice = ch
            ua.is_correct = bool(ch.is_correct)
            ua.selections = None
            ua.raw_answer = None
            if ua.is_correct:
                score = 1.0
        except Exception:
            if ua.choice and ua.is_correct:
                score = 1.0

    # -----------------------------
    # MULTI SELECT ✅ FIXED
    # -----------------------------
    elif q.question_type == "multi":
        posted_selections = post_data.getlist(f"question_{q.id}")

        # ✅ fallback to autosaved data
        if posted_selections:
            try:
                sel_ids = [int(x) for x in posted_selections if x]
            except ValueError:
                sel_ids = []
            ua.selections = sel_ids
        else:
            sel_ids = ua.selections or []

        ua.choice = None
        ua.raw_answer = None

        correct_ids = list(
            q.choices.filter(is_correct=True)
            .values_list("id", flat=True)
        )

        selected_set = set(sel_ids)
        correct_set = set(correct_ids)

        if not selected_set:
            ua.is_correct = False
            score = 0.0

        elif selected_set == correct_set:
            ua.is_correct = True
            score = 1.0

        elif selected_set.isdisjoint(correct_set):
            ua.is_correct = False
            score = 0.0

        else:
            ua.is_correct = None
            true_pos = len(selected_set & correct_set)
            false_pos = len(selected_set - correct_set)
            score = max(
                0.0,
                (true_pos - 0.5 * false_pos)
                / max(1, len(correct_set))
            )

    # -----------------------------
    # FILL IN THE BLANK
    # -----------------------------
    elif q.question_type == "fill":
        raw = (post_data.get(f"question_{q.id}") or "").strip()
        ua.raw_answer = raw
        ua.choice = None
        ua.selections = None

        if q.correct_text and normalize_text(raw) == normalize_text(q.correct_text):
            ua.is_correct = True
            score = 1.0
        else:
            ua.is_correct = False

    # -----------------------------
    # NUMERIC
    # -----------------------------
    elif q.question_type == "numeric":
        raw = (post_data.get(f"question_{q.id}") or "").strip()
        ua.raw_answer = raw
        ua.choice = None
        ua.selections = None

        try:
            val = float(raw)
            tol = q.numeric_tolerance or 0.0
            if q.numeric_answer is not None and abs(val - q.numeric_answer) <= tol:
                ua.is_correct = True
                score = 1.0
            else:
                ua.is_correct = False
        except Exception:
            ua.is_correct = False

    ua.save()
    return score


# --------------------------------------------------
# Grade FULL exam
# --------------------------------------------------

def grade_exam(
    ue: UserExam,
    post_data,
    *,
    is_mock: bool = False,
) -> Tuple[float, bool]:

    # Canonical question order
    if ue.question_order:
        qids = [int(x) for x in ue.question_order]
    else:
        qids = list(
            ue.answers.values_list("question_id", flat=True)
        )

    total = 0
    score_acc = 0.0

    for qid in qids:
        ua, _ = UserAnswer.objects.get_or_create(
            user_exam=ue,
            question_id=qid
        )
        total += 1
        score_acc += grade_answer(ua, post_data)

    score_percent = round((score_acc / total) * 100, 2) if total else 0.0

    passed = None if is_mock else score_percent >= (ue.exam.passing_score or 0)

    ue.score = score_percent
    ue.passed = passed
    ue.submitted_at = timezone.now()
    ue.save()

    return score_percent, passed
