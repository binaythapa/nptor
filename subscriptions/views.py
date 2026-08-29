# subscriptions/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Subscription,
    SubscriptionEntitlement,
    Payment,
)


@login_required
def subscription_history(request):
    """
    Display the authenticated user's subscription history.

    Subscription ownership and lifecycle are handled entirely
    by the subscriptions app.

    Architecture:

        Subscription
             ↓
        Entitlement
          ↙     ↘
       Track    Exam

        Subscription
             ↓
          Payment
    """

    # =========================================================
    # USER SUBSCRIPTIONS
    # =========================================================

    subscriptions = (
        Subscription.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "plan",
        )
        .prefetch_related(
            "entitlements__track",
            "entitlements__exam",
            "entitlements__course",
            "payments",
        )
        .order_by(
            "-created_at",
        )
    )

    # =========================================================
    # TRACK ENTITLEMENTS
    # =========================================================

    track_subs = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=request.user,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_TRACK
            ),
        )
        .select_related(
            "subscription",
            "subscription__plan",
            "track",
        )
        .order_by(
            "-created_at",
        )
    )

    # =========================================================
    # EXAM ENTITLEMENTS
    # =========================================================

    exam_subs = (
        SubscriptionEntitlement.objects
        .filter(
            subscription__user=request.user,
            resource_type=(
                SubscriptionEntitlement.RESOURCE_EXAM
            ),
        )
        .select_related(
            "subscription",
            "subscription__plan",
            "exam",
        )
        .order_by(
            "-created_at",
        )
    )

    # =========================================================
    # PAYMENT HISTORY
    # =========================================================

    payments = (
        Payment.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "subscription",
            "subscription__plan",
        )
        .order_by(
            "-paid_at",
            "-created_at",
        )
    )

    # =========================================================
    # RESPONSE
    # =========================================================

    return render(
        request,
        "quiz/student/subscription/history.html",
        {
            "subscriptions": subscriptions,
            "track_subs": track_subs,
            "exam_subs": exam_subs,
            "payments": payments,
            "now": timezone.now(),
        },
    )