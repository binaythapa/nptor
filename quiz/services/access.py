from django.utils import timezone
from quiz.models import ExamSubscription, ExamTrackSubscription


def can_access_exam(user, exam):
    """
    Returns:
        (True, None) if access allowed
        (False, reason_string) if denied
    """

    now = timezone.now()

    # =====================================================
    # TRACK-LEVEL SUBSCRIPTION
    # =====================================================
    if exam.track and exam.track.subscription_scope == exam.track.TRACK:

        track = exam.track

        sub = ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True
        ).first()

        if not sub:
            return False, "Subscription required for this track"

        # ---------- EXPIRY CHECK ----------
        if sub.expires_at and sub.expires_at < now:
            sub.is_active = False
            sub.save(update_fields=["is_active"])
            return False, "Subscription expired"

        # ---------- FREE / TRIAL / PAID ----------
        # Free track → always accessible
        if track.pricing_type == track.PRICING_FREE:
            return True, None

        # Paid track
        return True, None

    # =====================================================
    # EXAM-LEVEL SUBSCRIPTION
    # =====================================================
    sub = ExamSubscription.objects.filter(
        user=user,
        exam=exam,
        is_active=True
    ).first()

    if not sub:
        return False, "Subscription required for this exam"

    # ---------- EXPIRY CHECK ----------
    if sub.expires_at and sub.expires_at < now:
        sub.is_active = False
        sub.save(update_fields=["is_active"])
        return False, "Subscription expired"

    return True, None
