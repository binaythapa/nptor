from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from accounts.models import Notification


User = get_user_model()


def create_notification(recipient, notification_type, title, message, priority="info", target_url=None, metadata=None, dedupe_key=None):
    """Create one actionable in-app notification, safely deduplicated when requested."""
    if dedupe_key:
        existing = Notification.objects.filter(dedupe_key=dedupe_key).first()
        if existing:
            if recipient and not existing.recipients.filter(pk=recipient.pk).exists():
                existing.recipients.add(recipient)
            return existing
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                target_url=target_url,
                metadata=metadata or {},
                dedupe_key=dedupe_key,
            )
            if recipient:
                notification.recipients.add(recipient)
            return notification
    except IntegrityError:
        if dedupe_key:
            return Notification.objects.get(dedupe_key=dedupe_key)
        raise


def visible_notifications(user, unread_only=False):
    qs = Notification.objects.all().prefetch_related("recipients")
    if not user or not user.is_authenticated:
        return qs.none()
    visible = []
    for notification in qs:
        if not notification.is_visible_to(user):
            continue
        if unread_only and not notification.is_unread_for(user):
            continue
        visible.append(notification.pk)
    return Notification.objects.filter(pk__in=visible).order_by("-created_at")


def unread_notification_count(user):
    return visible_notifications(user, unread_only=True).count()


def mark_notification_read(notification, user=None):
    if user is None:
        return notification
    if notification.is_visible_to(user):
        notification.mark_as_read(user)
    return notification
