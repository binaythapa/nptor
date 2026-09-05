from django.shortcuts import get_object_or_404

from subscriptions.models import SubscriptionPlan


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


def get_default_plan():
    return (
        SubscriptionPlan.objects
        .filter(is_active=True)
        .order_by("price", "id")
        .first()
    )
