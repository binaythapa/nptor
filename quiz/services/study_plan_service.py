# quiz/services/study_plan_service.py

import random
from django.db import models, transaction
from django.utils import timezone
from quiz.models import StudyPlan, Question


PLAN_CONFIG = {
    7: {"days": 7, "per_day": 60},
    15: {"days": 15, "per_day": 40},
    30: {"days": 30, "per_day": 25},
}


def generate_study_plan(user, plan_type=15, domain=None, exam=None, daily_goal=None):
    """
    Creates a new study plan supporting 15-day balanced, 7-day crash, or 30-day mastery plans.
    Supports optional target exam or domain objective focus.
    Dynamically scales questions-per-day if the question pool is smaller than the target.
    Deactivates any existing active plan for the user.
    """
    plan_type = int(plan_type) if plan_type else 15
    if plan_type not in PLAN_CONFIG:
        plan_type = 15

    config = PLAN_CONFIG[plan_type]
    total_days = config["days"]
    default_per_day = config["per_day"]

    if daily_goal and int(daily_goal) > 0:
        per_day = int(daily_goal)
    else:
        per_day = default_per_day

    # Base active questions query
    qs = Question.objects.active()

    # Filter by target exam if specified
    if exam:
        exam_cat_ids = list(exam.categories.values_list("id", flat=True))
        alloc_cat_ids = list(exam.allocations.values_list("category_id", flat=True)) if hasattr(exam, "allocations") else []
        all_exam_cat_ids = list(set(exam_cat_ids) | set(alloc_cat_ids))

        if all_exam_cat_ids:
            qs = qs.filter(
                models.Q(primary_category_id__in=all_exam_cat_ids) |
                models.Q(categories__id__in=all_exam_cat_ids)
            )

    # Filter by domain objective if specified
    if domain:
        qs = qs.filter(
            models.Q(primary_category__domain=domain) |
            models.Q(categories__domain=domain)
        )

    question_ids = list(qs.distinct().values_list("id", flat=True))

    if not question_ids:
        raise ValueError("No questions available for the selected criteria. Please choose a different exam or domain.")

    # Shuffle question IDs (in Python memory, avoid order_by("?"))
    random.shuffle(question_ids)

    # Dynamic scaling for small question pools
    total_needed = total_days * per_day
    if len(question_ids) < total_needed:
        if len(question_ids) >= total_days:
            # Scale per_day to fit available questions
            per_day = max(1, len(question_ids) // total_days)
            total_needed = total_days * per_day
            selected_ids = question_ids[:total_needed]
        else:
            # Repeat questions to cover total_days with at least 1 question/day
            per_day = 1
            multiplier = (total_days // len(question_ids)) + 1
            selected_ids = (question_ids * multiplier)[:total_days]
    else:
        selected_ids = question_ids[:total_needed]

    with transaction.atomic():
        # Deactivate old active plans for this user
        StudyPlan.objects.filter(
            user=user,
            is_active=True,
        ).update(is_active=False)

        # Create new study plan
        plan = StudyPlan.objects.create(
            user=user,
            domain=domain,
            exam=exam,
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
    Auto extend plan if user missed a day up to MAX_EXTENSION_DAYS.
    """
    today_index = plan.get_day_index()

    if today_index >= plan.total_plan_days() and not plan.is_completed:
        if plan.extension_days < plan.MAX_EXTENSION_DAYS:
            plan.extension_days += 1
            plan.save(update_fields=["extension_days"])


def get_today_topics(plan):
    """
    Returns distinct category names for today's scheduled questions.
    """
    from quiz.models import Category
    today_ids = plan.get_today_question_ids()
    if not today_ids:
        return []

    cat_ids = Question.objects.filter(id__in=today_ids).values_list("primary_category_id", flat=True)
    categories = Category.objects.filter(id__in=set(filter(None, cat_ids)))
    return [c.name for c in categories]


def get_today_recommended_courses(plan):
    """
    Returns relevant courses matching the plan's domain or exam.
    """
    from courses.models.course import Course
    domain = plan.domain
    if not domain and plan.exam:
        cat = plan.exam.categories.select_related("domain").first()
        if cat and cat.domain:
            domain = cat.domain

    courses_qs = Course.objects.filter(
        is_published=True,
        approval_status=Course.APPROVAL_APPROVED,
    )
    if domain:
        courses_qs = courses_qs.filter(category=domain)

    return list(courses_qs.order_by("-created_at")[:3])
