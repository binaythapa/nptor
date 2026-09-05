from django.shortcuts import get_object_or_404

from subscriptions.models import SubscriptionPlan


def _active_plans(plans):
    return plans.filter(is_active=True).order_by("price", "id")


def get_default_plan(resource=None, plan_id=None):
    """Return the default active plan for legacy/admin callers.

    New resource-specific flows should use get_plan_for_track(),
    get_plan_for_course(), or get_plan_for_exam(). When a resource is supplied,
    its explicitly attached plans are preferred; otherwise the first active
    global plan is returned for backwards compatibility.
    """
    if resource is not None and hasattr(resource, "subscription_plans"):
        plans = _active_plans(resource.subscription_plans)
    else:
        plans = _active_plans(SubscriptionPlan.objects.all())

    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


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
