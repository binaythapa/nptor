from accounts.models import Notification


def unread_notifications_count(request):
    """
    Make the unread notification count available
    to every template.
    """

    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0,
        }

    try:

        notifications = Notification.objects.all()

        count = 0

        for notification in notifications:

            # Empty recipients = broadcast
            is_visible = (
                not notification.recipients.exists()
                or notification.recipients.filter(
                    id=request.user.id
                ).exists()
            )

            if not is_visible:
                continue

            if notification.is_unread_for(
                request.user
            ):
                count += 1

        return {
            "unread_notifications_count": count,
        }

    except Exception:

        return {
            "unread_notifications_count": 0,
        }