from accounts.models import Notification


def unread_notifications_count(request):
    """Make the unread notification count available to every template."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {"unread_notifications_count": 0}

    try:
        notifications = Notification.objects.all()
        count = 0
        for notification in notifications:
            is_visible = (
                not notification.recipients.exists()
                or notification.recipients.filter(id=user.id).exists()
            )
            if is_visible and notification.is_unread_for(user):
                count += 1
        return {"unread_notifications_count": count}
    except Exception:
        return {"unread_notifications_count": 0}
