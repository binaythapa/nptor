# subscriptions/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from orders.models import Order
from organizations.models.access import ResourceAccess
from .models import (
    AccountSubscriptionSelection,
    Payment,
    Subscription,
    SubscriptionEntitlement,
)
from .services.subscription_service import SubscriptionService


@login_required
def subscription_history(request):
    """Unified overview of the student's education subscriptions and Store orders.

    Maintains clean separation:
    - Education subscriptions provide learning course/track access and entitlements.
    - Store orders represent marketplace physical/digital merchandise purchases.
    """
    now = timezone.now()
    user = request.user

    # Fetch user subscriptions with real-time expiry check
    subscriptions_qs = (
        Subscription.objects
        .filter(user=user)
        .select_related("plan")
        .prefetch_related(
            "entitlements__track",
            "entitlements__course",
            "entitlements__exam",
            "account_selections__course",
            "account_selections__track",
            "payments",
        )
        .order_by("-created_at")
    )
    subscriptions = list(subscriptions_qs)
    for sub in subscriptions:
        SubscriptionService.expire_if_needed(sub)

    # Entitlement breakdowns
    course_subs = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=user,
            resource_type=SubscriptionEntitlement.RESOURCE_COURSE,
        )
        .select_related("subscription", "subscription__plan", "course")
        .order_by("-created_at")
    )

    track_subs = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=user,
            resource_type=SubscriptionEntitlement.RESOURCE_TRACK,
        )
        .select_related("subscription", "subscription__plan", "track")
        .order_by("-created_at")
    )

    exam_subs = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=user,
            resource_type=SubscriptionEntitlement.RESOURCE_EXAM,
        )
        .select_related("subscription", "subscription__plan", "exam")
        .order_by("-created_at")
    )

    account_selections = (
        AccountSubscriptionSelection.objects
        .filter(subscription__user=user)
        .select_related("subscription", "subscription__plan", "course", "track")
        .order_by("-created_at")
    )

    # Financial payment receipts for education subscriptions
    payments = (
        Payment.objects
        .filter(user=user)
        .select_related("subscription", "subscription__plan")
        .order_by("-paid_at", "-created_at")
    )

    # Separate Store marketplace orders
    store_orders = (
        Order.objects
        .filter(user=user)
        .select_related("shipping_address")
        .prefetch_related("suborders", "suborders__items", "suborders__vendor")
        .order_by("-created_at")[:20]
    )

    active_subscriptions_count = sum(1 for s in subscriptions if s.is_valid())
    active_tab = request.GET.get("tab", "subscriptions")
    if active_tab not in ("subscriptions", "orders"):
        active_tab = "subscriptions"

    return render(
        request,
        "quiz/student/subscription/history.html",
        {
            "subscriptions": subscriptions,
            "course_subs": course_subs,
            "track_subs": track_subs,
            "exam_subs": exam_subs,
            "account_selections": account_selections,
            "payments": payments,
            "store_orders": store_orders,
            "active_subscriptions_count": active_subscriptions_count,
            "total_orders_count": Order.objects.filter(user=user).count(),
            "active_tab": active_tab,
            "now": now,
        },
    )


@login_required
@require_POST
def cancel_user_subscription(request, subscription_id):
    """Allow an individual learner to cancel their active subscription."""
    subscription = get_object_or_404(
        Subscription.objects.select_related("plan"),
        id=subscription_id,
        user=request.user,
    )

    if subscription.status != Subscription.STATUS_ACTIVE:
        messages.error(request, "This subscription is not currently active.")
        return redirect("subscriptions:subscription_history")

    SubscriptionService.cancel(subscription, reason="User self-service cancellation")

    # Deactivate direct entitlements and individual access records
    subscription.entitlements.filter(is_active=True).update(is_active=False)
    ResourceAccess.objects.filter(
        user=request.user,
        subscription=subscription,
        is_active=True,
    ).update(is_active=False, revoked_at=timezone.now())

    messages.success(
        request,
        f"Your subscription to {subscription.plan.name} has been cancelled.",
    )
    return redirect("subscriptions:subscription_history")
