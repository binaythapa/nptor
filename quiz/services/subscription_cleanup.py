from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription


def expire_old_subscriptions():
    now = timezone.now()

    # --------- EXAM SUBSCRIPTIONS ---------
    ExamSubscription.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lt=now
    ).update(is_active=False)

    # --------- TRACK SUBSCRIPTIONS ---------
    ExamTrackSubscription.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lt=now
    ).update(is_active=False)
