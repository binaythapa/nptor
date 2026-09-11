from django.shortcuts import get_object_or_404

from subscriptions.models import SubscriptionPlan


def _active_plans(plans):
    return plans.filter(is_active=True).order_by("price", "id")


def get_default_plan(resource=None, plan_id=None):
    """Return the default active plan for legacy/admin callers."""
    if resource is not None and hasattr(resource, "subscription_plans"):
        plans = _active_plans(resource.subscription_plans)
    else:
        plans = _active_plans(SubscriptionPlan.objects.all())

    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_track(track, plan_id=None):
    plans = _active_plans(track.subscription_plans).filter(
        scope=SubscriptionPlan.SCOPE_RESOURCE,
    )
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_course(course, plan_id=None):
    """Return the canonical active resource plan attached to a course."""
    plans = _active_plans(course.subscription_plans).filter(
        scope=SubscriptionPlan.SCOPE_RESOURCE,
    )
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_exam(exam, plan_id=None):
    """Legacy helper retained for historical data; new checkout does not expose exams."""
    plans = _active_plans(exam.subscription_plans).filter(
        scope=SubscriptionPlan.SCOPE_RESOURCE,
    )
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_all_access_plans():
    """Return active plans that grant platform-wide access."""
    return _active_plans(
        SubscriptionPlan.objects.filter(
            scope=SubscriptionPlan.SCOPE_ALL_ACCESS,
        )
    )


def get_all_access_plan(plan_id=None):
    """Return a selected/default active platform-wide plan."""
    plans = get_all_access_plans()
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()
