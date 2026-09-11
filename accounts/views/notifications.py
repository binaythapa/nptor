from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Notification
from accounts.services.notifications import mark_notification_read, visible_notifications


@login_required
def notification_list(request):
    notifications = visible_notifications(request.user)[:50]
    unread_count = sum(1 for item in notifications if item.is_unread_for(request.user))
    return render(request, "accounts/notifications/list.html", {"notifications": notifications, "unread_count": unread_count})


@login_required
@require_POST
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    mark_notification_read(notification, request.user)
    return redirect(request.POST.get("next") or notification.target_url or "accounts:notifications")
