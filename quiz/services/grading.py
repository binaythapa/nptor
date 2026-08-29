from typing import Tuple

from django.utils import timezone

from quiz.models import (
    UserExam,
    UserAnswer,
    Question,
    Choice,
)


# ============================================================
# HELPERS
# ============================================================

def normalize_text(s: str) -> str:
    return " ".join((s or "").lower().split())


# ============================================================
# GRADE INDIVIDUAL ANSWER
# ============================================================

def grade_answer(
    ua: UserAnswer,
    post_data=None,
) -> float:

    q: Question = ua.question
    score = 0.0

    # Detect whether we are grading from submitted POST data
    # or grading from answers already saved in the database.
    use_post = post_data is not None

    # ========================================================
    # SINGLE / DROPDOWN / TRUE-FALSE
    # ========================================================

    if q.question_type in (
        "single",
        "dropdown",
        "tf",
    ):

        if use_post:

            choice_id = post_data.get(
                f"question_{q.id}"
            )

            if choice_id:

                try:

                    ch = Choice.objects.get(
                        pk=int(choice_id),
                        question=q,
                    )

                    ua.choice = ch

                except (
                    ValueError,
                    TypeError,
                    Choice.DoesNotExist,
                ):
                    pass

        # Grade saved choice

        if ua.choice:

            ua.is_correct = bool(
                ua.choice.is_correct
            )

            score = (
                1.0
                if ua.is_correct
                else 0.0
            )

        else:

            ua.is_correct = False
            score = 0.0

        ua.selections = None
        ua.raw_answer = None

    # ========================================================
    # MULTI SELECT
    # ========================================================

    elif q.question_type == "multi":

        if use_post:

            posted_selections = post_data.getlist(
                f"question_{q.id}"
            )

            try:

                ua.selections = [
                    int(x)
                    for x in posted_selections
                    if x
                ]

            except (
                ValueError,
                TypeError,
            ):

                ua.selections = []

        sel_ids = ua.selections or []

        correct_ids = list(
            q.choices
            .filter(is_correct=True)
            .values_list(
                "id",
                flat=True,
            )
        )

        selected_set = set(sel_ids)
        correct_set = set(correct_ids)

        if not selected_set:

            ua.is_correct = False
            score = 0.0

        elif selected_set == correct_set:

            ua.is_correct = True
            score = 1.0

        elif selected_set.isdisjoint(
            correct_set
        ):

            ua.is_correct = False
            score = 0.0

        else:

            ua.is_correct = None

            true_pos = len(
                selected_set & correct_set
            )

            false_pos = len(
                selected_set - correct_set
            )

            score = max(
                0.0,
                (
                    true_pos
                    - 0.5 * false_pos
                )
                / max(
                    1,
                    len(correct_set),
                ),
            )

        ua.choice = None
        ua.raw_answer = None

    # ========================================================
    # FILL IN THE BLANK
    # ========================================================

    elif q.question_type == "fill":

        if use_post:

            raw = (
                post_data.get(
                    f"question_{q.id}"
                )
                or ""
            ).strip()

            ua.raw_answer = raw

        raw = (
            ua.raw_answer or ""
        ).strip()

        if (
            q.correct_text
            and normalize_text(raw)
            == normalize_text(q.correct_text)
        ):

            ua.is_correct = True
            score = 1.0

        else:

            ua.is_correct = False
            score = 0.0

        ua.choice = None
        ua.selections = None

    # ========================================================
    # NUMERIC
    # ========================================================

    elif q.question_type == "numeric":

        if use_post:

            raw = (
                post_data.get(
                    f"question_{q.id}"
                )
                or ""
            ).strip()

            ua.raw_answer = raw

        raw = (
            ua.raw_answer or ""
        ).strip()

        try:

            val = float(raw)

            tol = (
                q.numeric_tolerance
                or 0.0
            )

            if (
                q.numeric_answer is not None
                and abs(
                    val
                    - q.numeric_answer
                ) <= tol
            ):

                ua.is_correct = True
                score = 1.0

            else:

                ua.is_correct = False
                score = 0.0

        except (
            ValueError,
            TypeError,
        ):

            ua.is_correct = False
            score = 0.0

        ua.choice = None
        ua.selections = None

    # ========================================================
    # SAVE ANSWER
    # ========================================================

    ua.save()

    return score


# ============================================================
# GRADE COMPLETE EXAM
# ============================================================

def grade_exam(
    ue: UserExam,
    post_data,
    *,
    is_mock: bool = False,
) -> Tuple[float, bool]:

    # ========================================================
    # QUESTION ORDER
    # ========================================================

    if ue.question_order:

        qids = [
            int(x)
            for x in ue.question_order
        ]

    else:

        qids = list(
            ue.answers.values_list(
                "question_id",
                flat=True,
            )
        )

    # ========================================================
    # GRADE ALL QUESTIONS
    # ========================================================

    total = 0
    score_acc = 0.0

    for qid in qids:

        ua, _ = (
            UserAnswer.objects.get_or_create(
                user_exam=ue,
                question_id=qid,
            )
        )

        total += 1

        score_acc += grade_answer(
            ua,
            post_data,
        )

    # ========================================================
    # CALCULATE SCORE
    # ========================================================

    score_percent = (
        round(
            (score_acc / total) * 100,
            2,
        )
        if total
        else 0.0
    )

    # ========================================================
    # PASS / FAIL
    # ========================================================

    passed = (
        None
        if is_mock
        else (
            score_percent
            >= (
                ue.exam.passing_score
                or 0
            )
        )
    )

    # ========================================================
    # FINALIZE EXAM
    # ========================================================

    ue.score = score_percent

    ue.passed = passed

    ue.submitted_at = timezone.now()

    # ⭐ IMPORTANT FIX
    # The previous code forgot this.
    ue.status = UserExam.STATUS_SUBMITTED

    ue.save(
        update_fields=[
            "score",
            "passed",
            "submitted_at",
            "status",
        ]
    )

    return score_percent, passed