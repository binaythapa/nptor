# quiz/services/study_plan_service.py

from django.utils import timezone
from django.db import transaction
from quiz.models import StudyPlan, Question


PLAN_CONFIG = {
    7: {"days": 1, "per_day": 1},    #60
    15: {"days": 15, "per_day": 40},  #40
    30: {"days": 30, "per_day": 25},  #25
}





import random


def generate_study_plan(user, plan_type, domain=None):
    """
    Creates a new study plan.
    Deactivates existing active plan.
    """

    if plan_type not in PLAN_CONFIG:
        raise ValueError("Invalid plan type.")

    config = PLAN_CONFIG[plan_type]
    total_days = config["days"]
    per_day = config["per_day"]
    total_needed = total_days * per_day

    # Fetch active question IDs (light query)
    qs = Question.objects.active()

    if domain:
        qs = qs.filter(category__domain=domain)

    question_ids = list(qs.values_list("id", flat=True))

    if len(question_ids) < total_needed:
        raise ValueError(
            f"Not enough questions. Required: {total_needed}, Available: {len(question_ids)}"
        )

    # Shuffle in Python (DO NOT use order_by("?"))
    random.shuffle(question_ids)

    selected_ids = question_ids[:total_needed]

    with transaction.atomic():
        # Deactivate old active plan
        StudyPlan.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)

        # Create new plan
        plan = StudyPlan.objects.create(
            user=user,
            domain=domain,
            plan_type=plan_type,
            total_days=total_days,
            questions_per_day=per_day,
            question_ids=selected_ids,
            start_date=timezone.now().date(),
            is_active=True,
        )

    return plan


def get_today_questions(plan):
    """
    Returns queryset for today's questions.
    """
    today_ids = plan.get_today_question_ids()

    return Question.objects.filter(id__in=today_ids)


def handle_missed_day(plan):
    """
    Auto extend plan if user missed a day.
    """

    today_index = plan.get_day_index()

    # If day index exceeds total plan days,
    # but plan not completed → extend
    if today_index >= plan.total_plan_days() and not plan.is_completed:
        plan.extension_days += 1
        plan.save(update_fields=["extension_days"])