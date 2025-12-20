import random
from collections import defaultdict
from quiz.models import Question, ExamCategoryAllocation


class ExamAllocationEngine:
    """
    Resolves exam questions ONCE per attempt.
    Stored in UserExam.question_order (immutable).
    """

    @staticmethod
    def allocate_questions(exam):
        total_required = exam.question_count
        selected_questions = []

        allocations = ExamCategoryAllocation.objects.filter(exam=exam)

        # -----------------------------
        # FIXED COUNTS FIRST
        # -----------------------------
        remaining_slots = total_required
        category_pool = defaultdict(list)

        for alloc in allocations:
            qs = Question.objects.filter(
                category__in=alloc.category.get_descendants_include_self()
            )
            category_pool[alloc.category_id] = list(qs)

            if alloc.fixed_count:
                picked = random.sample(
                    category_pool[alloc.category_id],
                    min(alloc.fixed_count, len(category_pool[alloc.category_id]))
                )
                selected_questions.extend(picked)
                remaining_slots -= len(picked)

        # -----------------------------
        # PERCENTAGE BASED
        # -----------------------------
        for alloc in allocations:
            if alloc.fixed_count:
                continue

            if remaining_slots <= 0:
                break

            pct_count = int((alloc.percentage / 100) * total_required)
            pct_count = min(pct_count, remaining_slots)

            pool = [
                q for q in category_pool[alloc.category_id]
                if q not in selected_questions
            ]

            picked = random.sample(pool, min(len(pool), pct_count))
            selected_questions.extend(picked)
            remaining_slots -= len(picked)

        # -----------------------------
        # FILL REMAINING
        # -----------------------------
        if remaining_slots > 0:
            extra_pool = Question.objects.filter(
                category__in=exam.categories.all()
            ).exclude(id__in=[q.id for q in selected_questions])

            selected_questions.extend(
                random.sample(
                    list(extra_pool),
                    min(remaining_slots, extra_pool.count())
                )
            )

        random.shuffle(selected_questions)
        return [q.id for q in selected_questions]
