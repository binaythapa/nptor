from django.shortcuts import get_object_or_404

from subscriptions.models import SubscriptionPlan


def _active_plans(plans):
    return plans.filter(is_active=True).order_by("price", "id")


def get_default_plan(resource=None, plan_id=None):
    """Return the default active plan for a legacy/admin caller."""
    if resource is not None and hasattr(resource, "subscription_plans"):
        plans = _active_plans(resource.subscription_plans)
    else:
        plans = _active_plans(SubscriptionPlan.objects.all())
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_track(track, plan_id=None):
    plans = _active_plans(track.subscription_plans).filter(
        product_type=SubscriptionPlan.PRODUCT_TRACK,
        access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
    )
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_plan_for_course(course, plan_id=None):
    plans = _active_plans(course.subscription_plans).filter(
        product_type=SubscriptionPlan.PRODUCT_COURSE,
        access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
    )
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()


def get_account_plans():
    return _active_plans(
        SubscriptionPlan.objects.filter(
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode__in=(
                SubscriptionPlan.ACCESS_LIMITED,
                SubscriptionPlan.ACCESS_ALL,
            ),
        )
    )


def get_all_access_plans():
    return _active_plans(
        SubscriptionPlan.objects.filter(
            product_type=SubscriptionPlan.PRODUCT_ACCOUNT,
            access_mode=SubscriptionPlan.ACCESS_ALL,
        )
    )


def get_all_access_plan(plan_id=None):
    plans = get_all_access_plans()
    if plan_id:
        return get_object_or_404(plans, id=plan_id)
    return plans.first()
