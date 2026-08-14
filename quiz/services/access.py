from django.utils import timezone

from quiz.models import (
    ExamSubscription,
    ExamTrackSubscription,
)


# ============================================================
# EXAM ACCESS
# ============================================================

def can_access_exam(user, exam):
    """
    Determine whether a user can access an exam.

    Returns:
        (True, None)
            Access is allowed.

        (False, reason)
            Access is denied.
    """

    now = timezone.now()

    # --------------------------------------------------------
    # USER AUTHENTICATION
    # --------------------------------------------------------

    if not user or not user.is_authenticated:
        return False, "Login required"

    # --------------------------------------------------------
    # EXAM PUBLISHED CHECK
    # --------------------------------------------------------

    if not exam.is_published:
        return False, "Exam is not published"

    # --------------------------------------------------------
    # FREE EXAM
    # --------------------------------------------------------

    if exam.is_free:
        return True, None

    # --------------------------------------------------------
    # TRACK-LEVEL SUBSCRIPTION
    #
    # A valid track subscription gives access to
    # all exams under that track.
    # --------------------------------------------------------

    if (
        exam.track
        and exam.track.subscription_scope
        == exam.track.TRACK
    ):
        track_subscription = (
            ExamTrackSubscription.objects.filter(
                user=user,
                track=exam.track,
                is_active=True,
            )
            .first()
        )

        if not track_subscription:
            return (
                False,
                "Subscription required for this track",
            )

        # ----------------------------------------------------
        # CHECK EXPIRATION
        # ----------------------------------------------------

        if (
            track_subscription.expires_at
            and track_subscription.expires_at <= now
        ):
            track_subscription.is_active = False

            track_subscription.save(
                update_fields=["is_active"]
            )

            return False, "Subscription expired"

        return True, None

    # --------------------------------------------------------
    # EXAM-LEVEL SUBSCRIPTION
    #
    # Used when the exam itself requires a subscription.
    # --------------------------------------------------------

    exam_subscription = (
        ExamSubscription.objects.filter(
            user=user,
            exam=exam,
            is_active=True,
        )
        .first()
    )

    if not exam_subscription:
        return (
            False,
            "Subscription required for this exam",
        )

    # --------------------------------------------------------
    # CHECK EXPIRATION
    # --------------------------------------------------------

    if (
        exam_subscription.expires_at
        and exam_subscription.expires_at <= now
    ):
        exam_subscription.is_active = False

        exam_subscription.save(
            update_fields=["is_active"]
        )

        return False, "Subscription expired"

    return True, None


# ============================================================
# ACTIVE TRACK SUBSCRIPTION
# ============================================================

def has_active_track_subscription(user, track):
    """
    Return True when the user has a valid active
    subscription for the specified ExamTrack.
    """

    if not user or not user.is_authenticated:
        return False

    if not track:
        return False

    now = timezone.now()

    subscription = (
        ExamTrackSubscription.objects.filter(
            user=user,
            track=track,
            is_active=True,
        )
        .first()
    )

    if not subscription:
        return False

    # --------------------------------------------------------
    # CHECK EXPIRATION
    # --------------------------------------------------------

    if (
        subscription.expires_at
        and subscription.expires_at <= now
    ):
        subscription.is_active = False

        subscription.save(
            update_fields=["is_active"]
        )

        return False

    return True


# ============================================================
# COURSE / TRACK ACCESS
# ============================================================

def user_has_course_access(user, course):
    """
    Determine whether a user has access to a course/track.

    Rules:

    1. No active subscription plans
       -> Course is free.

    2. Active subscription plans exist
       -> User must have an active ExamTrackSubscription.

    `course` is expected to be the ExamTrack object because
    ExamTrackSubscription.track points to ExamTrack.
    """

    if not user or not user.is_authenticated:
        return False

    if not course:
        return False

    # --------------------------------------------------------
    # ACTIVE SUBSCRIPTION PLANS
    # --------------------------------------------------------

    plans = course.subscription_plans.filter(
        is_active=True
    )

    # --------------------------------------------------------
    # FREE COURSE / TRACK
    # --------------------------------------------------------

    if not plans.exists():
        return True

    # --------------------------------------------------------
    # PAID COURSE / TRACK
    # --------------------------------------------------------

    return has_active_track_subscription(
        user=user,
        track=course,
    )