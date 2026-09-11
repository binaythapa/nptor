from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from subscriptions.services.plan_service import get_all_access_plans


@login_required
def subscription_plans(request):
    plans = get_all_access_plans()
    return render(request, "payments/subscription_plans.html", {"plans": plans})
