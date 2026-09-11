from accounts.services.notifications import unread_notification_count


def unread_notifications_count(request):
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}
    try:
        return {"unread_notifications_count": unread_notification_count(request.user)}
    except Exception:
        return {"unread_notifications_count": 0}
