# quiz/services/access.py

from subscriptions.services import AccessService
from quiz.models import UserExam
from quiz.services.track_progress import _published_track_exams, track_exam_lock


def has_resource_access(user, resource_type, resource, organization=None):
    if not user or not user.is_authenticated or not resource:
        return False
    return AccessService.has_access(
        student=user,
        resource_type=resource_type,
        resource=resource,
    )


def has_course_access(user, course, organization=None):
    return has_resource_access(user, AccessService.RESOURCE_COURSE, course, organization)


def has_track_access(user, track, organization=None):
    return has_resource_access(user, AccessService.RESOURCE_TRACK, track, organization)


def has_exam_access(user, exam, organization=None):
    return has_resource_access(user, AccessService.RESOURCE_EXAM, exam, organization)


def user_has_course_access(user, course, organization=None):
    return has_course_access(user, course, organization)


def has_active_track_subscription(user, track, organization=None):
    return has_track_access(user, track, organization)


def can_access_exam(user, exam, organization=None):
    """Return whether a published exam can be started through an owned track."""
    if not user or not user.is_authenticated:
        return False, "Login required"
    if not exam.is_published:
        return False, "Exam is not published"

    track_exams = list(
        exam.track_exams.select_related("track").filter(track__is_active=True)
    )
    if not track_exams:
        return False, "This exam is not included in an active track"

    had_track_access = False
    for membership in track_exams:
        track = membership.track
        if not has_track_access(user, track, organization):
            continue
        had_track_access = True
        locked, reason = track_exam_lock(
            user,
            exam,
            track=track,
        )
        if not locked:
            return True, None

    if had_track_access:
        return False, "Prerequisite exam required"
    return False, "Track access required"
