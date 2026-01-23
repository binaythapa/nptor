from quiz.models import ExamSubscription, ExamTrackSubscription
from django.utils import timezone


def has_active_exam_subscription(user, exam):
    return ExamSubscription.objects.filter(
        user=user,
        exam=exam,
        is_active=True
    ).filter(
        expires_at__isnull=True
        | models.Q(expires_at__gt=timezone.now())
    ).exists()


from django.utils import timezone
from quiz.models import ExamTrackSubscription


def has_active_track_subscription(user, track) -> bool:
    """
    Returns True if user has an active, non-expired subscription
    to the given track.
    """

    sub = ExamTrackSubscription.objects.filter(
        user=user,
        track=track,
        is_active=True
    ).first()

    if not sub:
        return False

    # ⏳ Expiry check
    if sub.expires_at and sub.expires_at < timezone.now():
        sub.is_active = False
        sub.save(update_fields=["is_active"])
        return False

    return True
