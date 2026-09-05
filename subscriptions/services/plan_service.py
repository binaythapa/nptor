from django.shortcuts import get_object_or_404


def _active_plans(plans):
    return plans.filter(is_active=True).order_by("price", "id")


def get_plan_for_track(track, plan_id=None):
    plans = _active_plans(track.subscription_plans)
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_course(course, plan_id=None):
    """Return the canonical active plan attached to a course."""
    plans = _active_plans(course.subscription_plans)
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_exam(exam, plan_id=None):
    """Return an active plan explicitly attached to the reusable exam."""
    plans = _active_plans(exam.subscription_plans)
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()
