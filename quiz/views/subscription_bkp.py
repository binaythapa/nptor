# quiz/views/subscription.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone


# ============================================================
# LEGACY SUBSCRIPTION HISTORY
#
# Temporary compatibility view.
#
# Checkout and subscription creation are no longer handled
# here. They are handled by:
#
#     payments
#         ↓
#     subscriptions
#
# This view will be migrated to the subscriptions app later.
# ============================================================

from quiz.models import (
    ExamSubscription,
    ExamTrackSubscription,
    PaymentRecord,
)


@login_required
def subscription_history(request):

    track_subs = (
        ExamTrackSubscription.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "track",
        )
        .order_by(
            "-subscribed_at",
        )
    )

    exam_subs = (
        ExamSubscription.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "exam",
        )
        .order_by(
            "-subscribed_at",
        )
    )

    payments = (
        PaymentRecord.objects
        .filter(
            user=request.user,
        )
        .select_related(
            "track",
            "exam",
        )
        .order_by(
            "-paid_at",
        )
    )

    return render(
        request,
        "quiz/subscription/history.html",
        {
            "track_subs": track_subs,
            "exam_subs": exam_subs,
            "payments": payments,
            "now": timezone.now(),
        },
    )


# ============================================================
# ENROLLMENT LEAD
#
# Temporary compatibility endpoint.
#
# This does not create a subscription or payment.
# ============================================================

@login_required
def log_enrollment_lead(request):

    item_type = request.POST.get(
        "type",
    )

    item_id = request.POST.get(
        "item_id",
    )

    if item_type not in (
        "exam",
        "track",
    ):
        return JsonResponse(
            {
                "ok": False,
            },
            status=400,
        )

    return JsonResponse(
        {
            "ok": True,
        }
    )