from typing import Tuple

from django.db import transaction
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
    # ORDERING
    # ========================================================

    elif q.question_type == "order":

        if use_post:
            selected = post_data.getlist(f"question_{q.id}")
            if selected:
                try:
                    ua.selections = [int(x) for x in selected]
                except (ValueError, TypeError):
                    ua.selections = []

        user_order = [int(x) for x in (ua.selections or [])]
        correct_order = list(
            Choice.objects.filter(question=q)
            .order_by("order", "id")
            .values_list("id", flat=True)
        )

        if user_order and user_order == correct_order:
            ua.is_correct = True
            score = 1.0
        else:
            ua.is_correct = False
            score = 0.0

        ua.choice = None
        ua.raw_answer = None

    # ========================================================
    # MATCHING
    # ========================================================

    elif q.question_type == "match":

        if use_post:
            match_map = {}
            prefix = f"match_{q.id}_"
            for k in post_data.keys():
                if k.startswith(prefix):
                    li = k[len(prefix):]
                    match_map[li] = post_data.get(k)
            if match_map:
                ua.selections = match_map

        user_matches = ua.selections or {}
        expected = q.matching_pairs or {}

        if isinstance(expected, dict) and user_matches:
            matches_correct = all(
                str(user_matches.get(str(k), "")) == str(v)
                for k, v in expected.items()
            )
            if matches_correct and len(user_matches) == len(expected):
                ua.is_correct = True
                score = 1.0
            else:
                ua.is_correct = False
                score = 0.0
        else:
            ua.is_correct = False
            score = 0.0

        ua.choice = None
        ua.raw_answer = None

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
    with transaction.atomic():
        locked_ue = UserExam.objects.select_for_update().get(pk=ue.pk)
        if locked_ue.submitted_at:
            ue.score = locked_ue.score
            ue.passed = locked_ue.passed
            ue.submitted_at = locked_ue.submitted_at
            ue.status = locked_ue.status
            return locked_ue.score or 0.0, locked_ue.passed

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

        now_time = timezone.now()
        locked_ue.score = score_percent
        locked_ue.passed = passed
        locked_ue.submitted_at = now_time
        locked_ue.status = UserExam.STATUS_SUBMITTED
        locked_ue.save(
            update_fields=[
                "score",
                "passed",
                "submitted_at",
                "status",
            ]
        )
        ue.score = locked_ue.score
        ue.passed = locked_ue.passed
        ue.submitted_at = locked_ue.submitted_at
        ue.status = locked_ue.status

        return score_percent, passed