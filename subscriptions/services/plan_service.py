# subscriptions/services/plan_service.py

from django.shortcuts import get_object_or_404

from subscriptions.models import SubscriptionPlan


def get_plan_for_track(track, plan_id=None):
    """
    Return an active subscription plan for a track.

    If plan_id is supplied:
        The plan must belong to the track and be active.

    Otherwise:
        Return the first active plan attached to the track,
        ordered by price and then ID.
    """

    plans = (
        track.subscription_plans
        .filter(
            is_active=True,
        )
        .order_by(
            "price",
            "id",
        )
    )

    if plan_id:
        return get_object_or_404(
            plans,
            id=plan_id,
        )

    return plans.first()


def get_default_plan():
    """
    Return the first active global subscription plan.

    Used as a fallback when an exam does not have
    a track-specific subscription plan.
    """

    return (
        SubscriptionPlan.objects
        .filter(
            is_active=True,
        )
        .order_by(
            "price",
            "id",
        )
        .first()
    )


def get_plan_for_exam(exam, plan_id=None):
    """
    Return a valid subscription plan for an exam.

    Preference:

        1. Explicit plan selected by admin
        2. Active plan attached to the exam's track
        3. First active global plan
    """

    if plan_id:
        return get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )

    if exam.track_id:
        plan = get_plan_for_track(
            exam.track,
        )

        if plan:
            return plan

    return get_default_plan()