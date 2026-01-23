from quiz.models import ExamTrackSubscription
from django.utils import timezone


def has_active_track_subscription(user, track):
    """
    Returns True if user has an active, non-expired subscription
    """
    sub = ExamTrackSubscription.objects.filter(
        user=user,
        track=track,
        is_active=True,
    ).first()

    if not sub:
        return False

    if sub.expires_at and sub.expires_at < timezone.now():
        sub.is_active = False
        sub.save(update_fields=["is_active"])
        return False

    return True
