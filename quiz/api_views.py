# ============================================================
# QUIZ API VIEWS
# ============================================================

from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated

from .models import (
    Exam,
    Question,
    Choice,
    UserExam,
    UserAnswer,
)

from .serializers import ExamSerializer

from quiz.services.exam_question_allocator import (
    allocate_questions_for_exam,
)


# ============================================================
# EXAM LIST API
# ============================================================

class ExamListAPI(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):

        exams = (
            Exam.objects
            .filter(
                is_published=True
            )
            .prefetch_related(
                "categories",
                "allocations__category",
            )
        )

        serializer = ExamSerializer(
            exams,
            many=True,
        )

        return Response(
            serializer.data
        )


# ============================================================
# START EXAM API
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_exam(request, pk):

    # ========================================================
    # LOAD EXAM
    # ========================================================

    exam = get_object_or_404(
        Exam,
        pk=pk,
        is_published=True,
    )

    # ========================================================
    # RESUME EXISTING ACTIVE ATTEMPT
    # ========================================================

    existing = (
        UserExam.objects
        .filter(
            user=request.user,
            exam=exam,
            submitted_at__isnull=True,
        )
        .first()
    )

    if existing:

        ue = existing

    else:

        # ====================================================
        # CREATE NEW ATTEMPT
        # ====================================================

        ue = UserExam.objects.create(
            user=request.user,
            exam=exam,
        )

        # ====================================================
        # ALLOCATE QUESTIONS
        # ====================================================

        questions = allocate_questions_for_exam(
            exam,
            seed=ue.id,
        )

        if not questions:

            ue.delete()

            return Response(
                {
                    "detail": (
                        "No questions are available "
                        "for this exam."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # STORE QUESTION ORDER
        # ====================================================

        ue.question_order = [
            question.id
            for question in questions
        ]

        ue.current_index = 0

        ue.save(
            update_fields=[
                "question_order",
                "current_index",
            ]
        )

        # ====================================================
        # CREATE USER ANSWERS
        # ====================================================

        UserAnswer.objects.bulk_create(
            [
                UserAnswer(
                    user_exam=ue,
                    question=question,
                )
                for question in questions
            ]
        )

    # ========================================================
    # BUILD QUESTION PAYLOAD
    # ========================================================

    question_ids = ue.question_order or []

    question_map = {
        question.id: question
        for question in (
            Question.objects
            .filter(
                id__in=question_ids
            )
            .prefetch_related("choices")
        )
    }

    payload = []

    for question_id in question_ids:

        question = question_map.get(
            question_id
        )

        if not question:
            continue

        # ----------------------------------------------------
        # CHOICES
        # ----------------------------------------------------

        if question.question_type in (
            "single",
            "multi",
            "tf",
            "dropdown",
        ):

            choices = [
                {
                    "id": choice.id,
                    "text": choice.text,
                }
                for choice in question.choices.all()
            ]

        else:

            choices = []

        # ----------------------------------------------------
        # QUESTION PAYLOAD
        # ----------------------------------------------------

        payload.append(
            {
                "question_id": question.id,
                "text": question.text,
                "question_type": (
                    question.question_type
                ),
                "difficulty": question.difficulty,

                "allow_multiple": (
                    question.question_type
                    == "multi"
                ),

                "choices": choices,

                "matching_pairs": (
                    question.matching_pairs
                ),

                "ordering_items": (
                    question.ordering_items
                ),

                "numeric_tolerance": (
                    question.numeric_tolerance
                ),
            }
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return Response(
        {
            "attempt_id": ue.id,
            "exam_id": exam.id,
            "duration_seconds": (
                ue.exam.duration_seconds
            ),
            "question_count": len(payload),
            "questions": payload,
        }
    )


# ============================================================
# ATTEMPT DETAIL API
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def attempt_detail(
    request,
    attempt_id,
):

    ue = get_object_or_404(
        UserExam,
        pk=attempt_id,
        user=request.user,
    )

    # ========================================================
    # QUESTION ANSWERS
    # ========================================================

    data = []

    answers = (
        ue.answers
        .select_related(
            "question",
            "choice",
        )
        .all()
    )

    for ua in answers:

        data.append(
            {
                "question_id": (
                    ua.question.id
                ),

                "question": (
                    ua.question.text
                ),

                "question_type": (
                    ua.question.question_type
                ),

                "selected_choice": (
                    ua.choice.id
                    if ua.choice
                    else None
                ),

                "selections": (
                    ua.selections
                ),

                "raw_answer": (
                    ua.raw_answer
                ),
            }
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return Response(
        {
            "attempt": ue.id,
            "exam_id": ue.exam_id,
            "time_remaining": (
                ue.time_remaining()
            ),
            "submitted": (
                ue.submitted_at is not None
            ),
            "questions": data,
        }
    )


# ============================================================
# SUBMIT ATTEMPT API
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def api_submit_attempt(
    request,
    attempt_id,
):

    ue = get_object_or_404(
        UserExam,
        pk=attempt_id,
        user=request.user,
    )

    # ========================================================
    # ALREADY SUBMITTED
    # ========================================================

    if ue.submitted_at:

        return Response(
            {
                "detail": "Attempt already submitted.",
                "score": ue.score,
            },
            status=status.HTTP_409_CONFLICT,
        )

    # ========================================================
    # CHECK ACTIVE ATTEMPT
    # ========================================================

    if not ue.is_active():

        return Response(
            {
                "detail": "Attempt closed."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ========================================================
    # ANSWERS
    # ========================================================

    answers = request.data.get(
        "answers",
        {},
    )

    if not isinstance(answers, dict):

        return Response(
            {
                "detail": (
                    "answers must be an object."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ========================================================
    # SCORE STATE
    # ========================================================

    total = 0
    score_acc = 0.0

    # ========================================================
    # PROCESS ANSWERS
    # ========================================================

    for ua in (
        ue.answers
        .select_related("question")
        .all()
    ):

        question = ua.question

        total += 1

        question_key = str(
            question.id
        )

        submitted_answer = answers.get(
            question_key
        )

        # ====================================================
        # SINGLE / TF / DROPDOWN
        # ====================================================

        if question.question_type in (
            "single",
            "tf",
            "dropdown",
        ):

            choice_id = submitted_answer

            if choice_id:

                try:

                    choice = (
                        Choice.objects
                        .get(
                            pk=int(choice_id),
                            question=question,
                        )
                    )

                    ua.choice = choice

                    ua.is_correct = (
                        choice.is_correct
                    )

                    if ua.is_correct:
                        score_acc += 1.0

                except (
                    ValueError,
                    TypeError,
                    Choice.DoesNotExist,
                ):

                    ua.choice = None
                    ua.is_correct = False

            else:

                ua.choice = None
                ua.is_correct = False

            ua.selections = None
            ua.raw_answer = None

            ua.save()

        # ====================================================
        # MULTIPLE CHOICE
        # ====================================================

        elif question.question_type == "multi":

            selected = (
                submitted_answer
                if isinstance(
                    submitted_answer,
                    list,
                )
                else []
            )

            selected_ids = []

            for value in selected:

                try:

                    selected_ids.append(
                        int(value)
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    continue

            selected_ids = list(
                dict.fromkeys(
                    selected_ids
                )
            )

            ua.selections = selected_ids

            correct_ids = list(
                question.choices
                .filter(
                    is_correct=True
                )
                .values_list(
                    "id",
                    flat=True,
                )
            )

            correct_set = set(
                correct_ids
            )

            selected_set = set(
                selected_ids
            )

            if not correct_set:

                frac = 0.0

            else:

                true_positive = len(
                    selected_set
                    & correct_set
                )

                false_positive = len(
                    selected_set
                    - correct_set
                )

                frac = max(
                    0.0,
                    (
                        true_positive
                        - (
                            0.5
                            * false_positive
                        )
                    )
                    / len(correct_set),
                )

            score_acc += frac

            # Exact correctness

            ua.is_correct = (
                selected_set
                == correct_set
            )

            ua.choice = None
            ua.raw_answer = None

            ua.save()

        # ====================================================
        # FILL IN THE BLANK
        # ====================================================

        elif question.question_type == "fill":

            raw = (
                submitted_answer
                or ""
            )

            raw = str(raw).strip()

            ua.raw_answer = raw

            def normalize(value):

                return " ".join(
                    str(value)
                    .lower()
                    .split()
                )

            if question.correct_text:

                ua.is_correct = (
                    normalize(raw)
                    == normalize(
                        question.correct_text
                    )
                )

                if ua.is_correct:

                    score_acc += 1.0

            else:

                ua.is_correct = False

            ua.selections = None
            ua.choice = None

            ua.save()

        # ====================================================
        # NUMERIC
        # ====================================================

        elif question.question_type == "numeric":

            raw = (
                submitted_answer
                or ""
            )

            raw = str(raw).strip()

            ua.raw_answer = raw

            try:

                value = float(raw)

                if (
                    question.numeric_answer
                    is not None
                ):

                    tolerance = (
                        question.numeric_tolerance
                        or 0.0
                    )

                    ua.is_correct = (
                        abs(
                            value
                            - float(
                                question.numeric_answer
                            )
                        )
                        <= float(
                            tolerance
                        )
                    )

                    if ua.is_correct:

                        score_acc += 1.0

                else:

                    ua.is_correct = False

            except (
                ValueError,
                TypeError,
            ):

                ua.is_correct = False

            ua.selections = None
            ua.choice = None

            ua.save()

        # ====================================================
        # MATCHING
        # ====================================================

        elif question.question_type == "match":

            pairs = (
                question.matching_pairs
                or []
            )

            true_positive = 0
            false_positive = 0

            for index, pair in enumerate(
                pairs
            ):

                selected_value = answers.get(
                    f"{question.id}_{index}"
                )

                expected_value = (
                    pair.get("right")
                    if isinstance(
                        pair,
                        dict,
                    )
                    else None
                )

                if (
                    selected_value
                    and str(
                        selected_value
                    )
                    == str(
                        expected_value
                    )
                ):

                    true_positive += 1

                else:

                    false_positive += 1

            denominator = (
                len(pairs)
                if pairs
                else 1
            )

            frac = max(
                0.0,
                (
                    true_positive
                    - (
                        0.5
                        * false_positive
                    )
                )
                / denominator,
            )

            score_acc += frac

            ua.selections = None
            ua.choice = None
            ua.raw_answer = None

            ua.is_correct = (
                true_positive
                == len(pairs)
                if pairs
                else False
            )

            ua.save()

        # ====================================================
        # ORDERING
        # ====================================================

        elif question.question_type == "order":

            raw = (
                submitted_answer
                or ""
            )

            raw = str(raw).strip()

            ua.raw_answer = raw

            try:

                user_order = [
                    item.strip()
                    for item in raw.split(",")
                    if item.strip()
                ]

                canonical = (
                    question.ordering_items
                    or []
                )

                denominator = max(
                    1,
                    len(canonical),
                )

                correct_positions = 0

                for index, value in enumerate(
                    user_order
                ):

                    if (
                        index
                        < len(canonical)
                        and str(
                            canonical[index]
                        ).strip().lower()
                        == value.strip().lower()
                    ):

                        correct_positions += 1

                frac = (
                    correct_positions
                    / denominator
                )

                score_acc += frac

                ua.is_correct = (
                    user_order
                    == [
                        str(item)
                        for item in canonical
                    ]
                )

            except Exception:

                ua.is_correct = False

            ua.selections = None
            ua.choice = None

            ua.save()

        # ====================================================
        # UNKNOWN QUESTION TYPE
        # ====================================================

        else:

            ua.choice = None
            ua.is_correct = False
            ua.selections = None
            ua.raw_answer = None

            ua.save()

    # ========================================================
    # FINAL SCORE
    # ========================================================

    ue.score = (
        (score_acc / total) * 100
        if total
        else 0
    )

    # ========================================================
    # PASS / FAIL
    # ========================================================

    ue.passed = (
        ue.score >= ue.exam.passing_score
    )

    # ========================================================
    # SUBMIT
    # ========================================================

    ue.submitted_at = timezone.now()

    ue.save(
        update_fields=[
            "score",
            "passed",
            "submitted_at",
        ]
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return Response(
        {
            "attempt_id": ue.id,
            "score": ue.score,
            "passed": ue.passed,
            "submitted_at": (
                ue.submitted_at
            ),
        }
    )