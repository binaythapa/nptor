from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils.timezone import now

from organizations.permissions import platform_admin_required
from quiz.models import UserExam
from subscriptions.models import SubscriptionEntitlement


User = get_user_model()


@platform_admin_required
def user_monitoring(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.select_related("profile").annotate(
        total_attempts=Count("exam_attempts", distinct=True),
        avg_score=Avg("exam_attempts__score"),
        active_entitlements=Count("subscription__entitlements", filter=Q(subscription__entitlements__is_active=True), distinct=True),
    )
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
    users = users.order_by("-date_joined")
    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "accounts/admin/user_monitoring.html", {"users": page, "page_obj": page, "search_query": query, "current_time": now()})
