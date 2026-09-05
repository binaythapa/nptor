# quiz/services/access.py

from subscriptions.services import AccessService
from quiz.models import UserExam
from quiz.services.track_progress import track_exam_lock


# ============================================================
# GENERIC RESOURCE ACCESS
# ============================================================

def has_resource_access(
    user,
    resource_type,
    resource,
    organization=None,
):
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
    """Return whether the user can start an exam and why when blocked."""
    if not user or not user.is_authenticated:
        return False, "Login required"

    if not exam.is_published:
        return False, "Exam is not published"

    prerequisite_ids = list(
        exam.prerequisite_exams.values_list("id", flat=True)
    )
    if prerequisite_ids:
        passed_count = (
            UserExam.objects.filter(
                user=user,
                exam_id__in=prerequisite_ids,
                submitted_at__isnull=False,
                passed=True,
            )
            .values("exam_id")
            .distinct()
            .count()
        )
        if passed_count != len(set(prerequisite_ids)):
            return False, "Prerequisite exam required"

    # Track progression is checked before entitlement so a paid track
    # subscription cannot bypass an exam-order or score requirement.
    track_locked, track_reason = track_exam_lock(user, exam)
    if track_locked:
        return False, track_reason

    if exam.is_free:
        return True, None

    if has_exam_access(user=user, exam=exam, organization=organization):
        return True, None

    if exam.track and has_track_access(
        user=user,
        track=exam.track,
        organization=organization,
    ):
        return True, None

    return False, "Subscription required"
