from subscriptions.services import AccessService
from quiz.models import UserExam
from quiz.services.track_progress import track_exam_lock


# ============================================================
# GENERIC RESOURCE ACCESS
# ============================================================

def has_resource_access(user, resource_type, resource, organization=None):
    """Central access check for Course / Track / Exam."""
    if not user or not user.is_authenticated:
        return False
    if not resource:
        return False
    return AccessService.has_access(
        student=user,
        resource_type=resource_type,
        resource=resource,
    )


def has_course_access(user, course, organization=None):
    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
        organization=organization,
    )


def has_track_access(user, track, organization=None):
    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
        organization=organization,
    )


def has_exam_access(user, exam, organization=None):
    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_EXAM,
        resource=exam,
        organization=organization,
    )


def user_has_course_access(user, course, organization=None):
    return has_course_access(user=user, course=course, organization=organization)


def has_active_track_subscription(user, track, organization=None):
    return has_track_access(user=user, track=track, organization=organization)


def can_access_exam(user, exam, organization=None):
    """Return whether the user can start an exam and why when blocked.

    Direct exam entitlements and track entitlements are evaluated separately.
    Track-specific ordering and prerequisites are enforced only when access is
    granted through that track, so reusing an exam across tracks is safe.
    """
    if not user or not user.is_authenticated:
        return False, "Login required"

    if not exam.is_published:
        return False, "Exam is not published"

    # A direct exam entitlement always grants direct exam access. The exam's
    # track-specific prerequisites are intentionally not applied here because
    # they belong to the track relationship, not to the reusable exam.
    if has_exam_access(user=user, exam=exam, organization=organization):
        return True, None

    memberships = list(
        exam.track_memberships.filter(
            track__is_active=True,
            track__organization__isnull=True,
        )
        .select_related("track")
        .prefetch_related("prerequisite_exams")
    )

    for membership in memberships:
        track = membership.track
        if not (track.is_free() or has_track_access(user=user, track=track, organization=organization)):
            continue

        locked, reason = track_exam_lock(
            user=user,
            exam=exam,
            track=track,
        )
        if not locked:
            return True, None

    # An exam with no track membership and no direct paid plan is a standalone
    # free exam. An exam attached to a track is governed by that track instead.
    if not memberships and exam.is_free:
        return True, None

    return False, "Subscription required"
