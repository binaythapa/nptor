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


def has_active_track_subscription(user, track):
    return ExamTrackSubscription.objects.filter(
        user=user,
        track=track,
        is_active=True
    ).filter(
        expires_at__isnull=True
        | models.Q(expires_at__gt=timezone.now())
    ).exists()
