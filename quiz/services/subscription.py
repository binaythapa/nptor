from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription

def has_valid_subscription(user, exam):
    track = exam.track

    # Track-level subscription
    if track and track.subscription_scope == "track":
        sub = ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True
        ).first()
        return sub and sub.is_valid()

    # Exam-level subscription
    sub = ExamSubscription.objects.filter(
        user=user,
        exam=exam,
        is_active=True
    ).first()
    return sub and sub.is_valid()
