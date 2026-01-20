from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription


def can_access_exam(user, exam):
    """
    Returns:
        (True, None) if access allowed
        (False, reason_string) if denied
    """

    now = timezone.now()

    # -------------------------------------------------
    # BLOCK UNPUBLISHED EXAMS
    # -------------------------------------------------
    if not exam.is_published:
        return False, "Exam is not published"

    # -------------------------------------------------
    # FREE EXAM (NO SUBSCRIPTION REQUIRED)
    # -------------------------------------------------
    if exam.is_free:
        return True, None

    # -------------------------------------------------
    # TRACK-LEVEL SUBSCRIPTION
    # -------------------------------------------------
    if exam.track and exam.track.subscription_scope == exam.track.TRACK:
        track = exam.track

        sub = ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True
        ).first()

        if not sub:
            return False, "Subscription required for this track"

        if sub.expires_at and sub.expires_at < now:
            sub.is_active = False
            sub.save(update_fields=["is_active"])
            return False, "Subscription expired"

        # Track subscription grants access to all exams
        return True, None

    # -------------------------------------------------
    # EXAM-LEVEL SUBSCRIPTION
    # -------------------------------------------------
    sub = ExamSubscription.objects.filter(
        user=user,
        exam=exam,
        is_active=True
    ).first()

    if not sub:
        return False, "Subscription required for this exam"

    if sub.expires_at and sub.expires_at < now:
        sub.is_active = False
        sub.save(update_fields=["is_active"])
        return False, "Subscription expired"

    return True, None
