from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from subscriptions.models import Subscription
from subscriptions.services.global_access import has_all_access_subscription
from subscriptions.services.plan_service import (
    get_all_access_plans,
    get_account_plans,
)


@login_required
def subscription_plans(request):
    """Present eligible education access plans and current subscription status."""
    now = timezone.now()
    user = request.user

    all_access_plans = get_all_access_plans()
    account_plans = get_account_plans().exclude(id__in=all_access_plans.values_list("id", flat=True))

    active_subscriptions = list(
        Subscription.objects
        .filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
            starts_at__lte=now,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .select_related("plan")
        .order_by("-created_at")
    )

    current_subscription = active_subscriptions[0] if active_subscriptions else None
    user_has_all_access = has_all_access_subscription(user)

    return render(
        request,
        "payments/subscription_plans.html",
        {
            "plans": all_access_plans,
            "account_plans": account_plans,
            "current_subscription": current_subscription,
            "has_all_access": user_has_all_access,
            "active_subscriptions_count": len(active_subscriptions),
            "now": now,
        },
    )
