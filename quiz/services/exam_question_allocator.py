import math
import random

from django.db.models import Q

from quiz.models import Question


def allocate_questions_for_exam(exam, seed=None):
    """
    Enterprise question allocation engine.

    Supports:

    - Fixed-count allocations
    - Percentage allocations
    - Category hierarchy
    - include_descendants
    - Question primary_category
    - Question multiple categories
    - Questions shared across multiple exams
    - Duplicate prevention
    - Deterministic selection using seed
    - Active questions only
    - Soft-deleted questions excluded
    - Organization / tenant isolation
    - Primary exam category
    - Multiple exam categories
    - Safe final fallback

    Important:

    A Question does NOT belong exclusively to one exam.

    The same question can be used by:

        SnowPro Core
        SnowPro Architect
        Snowflake Security
        Snowflake Administration

    because exam membership is determined by the exam's
    category blueprint, not by an exam FK on Question.
    """

    # =========================================================
    # TOTAL QUESTIONS
    # =========================================================

    total_needed = int(exam.question_count or 0)

    if total_needed <= 0:
        return []

    # =========================================================
    # RANDOM GENERATOR
    # =========================================================

    rng = random.Random(seed)

    # =========================================================
    # BASE QUESTION QUERYSET
    # =========================================================

    base_qs = Question.objects.filter(
        is_active=True,
        is_deleted=False,
    )

    # =========================================================
    # TENANT ISOLATION
    # =========================================================

    if exam.organization_id:

        base_qs = base_qs.filter(
            organization_id=exam.organization_id
        )

    else:

        # Global exams may only use global questions.

        base_qs = base_qs.filter(
            organization__isnull=True
        )

    # =========================================================
    # ALLOCATIONS
    # =========================================================

    allocations = list(
        exam.allocations
        .select_related("category")
        .all()
    )

    # =========================================================
    # CATEGORY HELPER
    # =========================================================

    def get_category_ids(category, include_descendants=True):
        """
        Return category IDs.

        Example hierarchy:

            Snowflake
            ├── Architecture
            │   ├── SnowPro Core
            │   └── SnowPro Architect
            ├── Security
            └── Performance

        If include_descendants=True and the allocation is
        Architecture, questions from Architecture and all
        child categories are eligible.
        """

        if not category:
            return set()

        if not include_descendants:
            return {category.id}

        try:
            return set(
                category.get_descendants_include_self()
            )
        except Exception:
            return {category.id}

    # =========================================================
    # QUESTION POOL HELPER
    # =========================================================

    selected_ids = set()

    def get_question_pool(category_ids):
        """
        Return questions matching the supplied categories.

        A question qualifies when:

            Question.primary_category
                matches

        OR

            Question.categories
                contains a matching category.

        DISTINCT prevents duplicate rows caused by the M2M join.
        """

        if not category_ids:
            return []

        qs = (
            base_qs
            .filter(
                Q(
                    primary_category_id__in=category_ids
                )
                |
                Q(
                    categories__id__in=category_ids
                )
            )
            .exclude(
                id__in=selected_ids
            )
            .distinct()
            .order_by()
        )

        return list(qs)

    # =========================================================
    # SELECTION STATE
    # =========================================================

    selected_questions = []

    remaining_needed = total_needed

    # =========================================================
    # NO BLUEPRINT
    # =========================================================

    if not allocations:

        category_ids = set()

        # -----------------------------------------------------
        # Primary exam category
        # -----------------------------------------------------

        if exam.primary_category_id:

            category_ids.update(
                get_category_ids(
                    exam.primary_category,
                    include_descendants=True,
                )
            )

        # -----------------------------------------------------
        # Multiple exam categories
        # -----------------------------------------------------

        for category in exam.categories.all():

            category_ids.update(
                get_category_ids(
                    category,
                    include_descendants=True,
                )
            )

        # -----------------------------------------------------
        # Category-based selection
        # -----------------------------------------------------

        if category_ids:

            pool = get_question_pool(
                category_ids
            )

            rng.shuffle(pool)

            chosen = pool[:remaining_needed]

            selected_questions.extend(
                chosen
            )

            selected_ids.update(
                question.id
                for question in chosen
            )

            remaining_needed = (
                total_needed
                - len(selected_questions)
            )

        # -----------------------------------------------------
        # Final tenant-safe fallback
        # -----------------------------------------------------

        if remaining_needed > 0:

            pool = list(
                base_qs
                .exclude(
                    id__in=selected_ids
                )
                .order_by()
            )

            rng.shuffle(pool)

            chosen = pool[:remaining_needed]

            selected_questions.extend(
                chosen
            )

            selected_ids.update(
                question.id
                for question in chosen
            )

        rng.shuffle(
            selected_questions
        )

        return selected_questions[
            :total_needed
        ]

    # =========================================================
    # FIXED ALLOCATION VALIDATION
    # =========================================================

    fixed_total = sum(
        allocation.fixed_count or 0
        for allocation in allocations
    )

    if fixed_total > total_needed:

        raise ValueError(
            "Fixed category allocation exceeds "
            "the exam question count."
        )

    # =========================================================
    # PERCENTAGE ALLOCATIONS
    # =========================================================

    percentage_allocations = []

    percentage_total = 0

    # =========================================================
    # 1. FIXED ALLOCATIONS
    # =========================================================

    for allocation in allocations:

        if allocation.fixed_count is not None:

            category_ids = get_category_ids(
                allocation.category,
                include_descendants=getattr(
                    allocation,
                    "include_descendants",
                    True,
                ),
            )

            pool = get_question_pool(
                category_ids
            )

            rng.shuffle(pool)

            take = min(
                allocation.fixed_count,
                len(pool),
                remaining_needed,
            )

            chosen = pool[:take]

            selected_questions.extend(
                chosen
            )

            selected_ids.update(
                question.id
                for question in chosen
            )

            remaining_needed -= take

        elif allocation.percentage is not None:

            percentage_allocations.append(
                allocation
            )

            percentage_total += (
                allocation.percentage
            )

    # =========================================================
    # 2. PERCENTAGE ALLOCATIONS
    # =========================================================

    if (
        percentage_allocations
        and remaining_needed > 0
        and percentage_total > 0
    ):

        calculated = []

        for allocation in percentage_allocations:

            raw_count = (
                allocation.percentage
                / percentage_total
                * remaining_needed
            )

            floor_count = math.floor(
                raw_count
            )

            remainder = (
                raw_count - floor_count
            )

            calculated.append(
                (
                    allocation,
                    floor_count,
                    remainder,
                )
            )

        percentage_counts = {
            allocation.id: floor_count
            for (
                allocation,
                floor_count,
                _,
            ) in calculated
        }

        allocated = sum(
            percentage_counts.values()
        )

        leftover = (
            remaining_needed
            - allocated
        )

        # -----------------------------------------------------
        # Largest remainder method
        # -----------------------------------------------------

        sorted_allocations = sorted(
            calculated,
            key=lambda item: item[2],
            reverse=True,
        )

        index = 0

        while (
            leftover > 0
            and sorted_allocations
        ):

            allocation = sorted_allocations[
                index % len(sorted_allocations)
            ][0]

            percentage_counts[
                allocation.id
            ] += 1

            leftover -= 1
            index += 1

        # -----------------------------------------------------
        # Select percentage questions
        # -----------------------------------------------------

        for allocation in percentage_allocations:

            requested_count = (
                percentage_counts.get(
                    allocation.id,
                    0,
                )
            )

            if requested_count <= 0:
                continue

            category_ids = get_category_ids(
                allocation.category,
                include_descendants=getattr(
                    allocation,
                    "include_descendants",
                    True,
                ),
            )

            pool = get_question_pool(
                category_ids
            )

            rng.shuffle(pool)

            chosen = pool[
                :requested_count
            ]

            selected_questions.extend(
                chosen
            )

            selected_ids.update(
                question.id
                for question in chosen
            )

        remaining_needed = (
            total_needed
            - len(selected_questions)
        )

    # =========================================================
    # 3. PRIMARY EXAM CATEGORY FALLBACK
    # =========================================================

    if (
        remaining_needed > 0
        and exam.primary_category_id
    ):

        category_ids = get_category_ids(
            exam.primary_category,
            include_descendants=True,
        )

        pool = get_question_pool(
            category_ids
        )

        rng.shuffle(pool)

        chosen = pool[
            :remaining_needed
        ]

        selected_questions.extend(
            chosen
        )

        selected_ids.update(
            question.id
            for question in chosen
        )

        remaining_needed = (
            total_needed
            - len(selected_questions)
        )

    # =========================================================
    # 4. MULTI-CATEGORY EXAM FALLBACK
    # =========================================================

    if (
        remaining_needed > 0
        and exam.categories.exists()
    ):

        category_ids = set()

        for category in exam.categories.all():

            category_ids.update(
                get_category_ids(
                    category,
                    include_descendants=True,
                )
            )

        pool = get_question_pool(
            category_ids
        )

        rng.shuffle(pool)

        chosen = pool[
            :remaining_needed
        ]

        selected_questions.extend(
            chosen
        )

        selected_ids.update(
            question.id
            for question in chosen
        )

        remaining_needed = (
            total_needed
            - len(selected_questions)
        )

    # =========================================================
    # 5. FINAL TENANT-SAFE FALLBACK
    # =========================================================

    if remaining_needed > 0:

        pool = list(
            base_qs
            .exclude(
                id__in=selected_ids
            )
            .order_by()
        )

        rng.shuffle(pool)

        chosen = pool[
            :remaining_needed
        ]

        selected_questions.extend(
            chosen
        )

        selected_ids.update(
            question.id
            for question in chosen
        )

    # =========================================================
    # FINAL SHUFFLE
    # =========================================================

    rng.shuffle(
        selected_questions
    )

    return selected_questions[
        :total_needed
    ]