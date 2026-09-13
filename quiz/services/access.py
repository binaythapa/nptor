from subscriptions.services import AccessService
from quiz.services.track_progress import track_exam_lock


def has_resource_access(user, resource_type, resource, organization=None):
    """Central access check for Course / Track / Exam."""
    if not user or not user.is_authenticated:
        return False
    if not resource:
        return False
    return AccessService.has_access(student=user, resource_type=resource_type, resource=resource)


def has_course_access(user, course, organization=None):
    return has_resource_access(user=user, resource_type=AccessService.RESOURCE_COURSE, resource=course, organization=organization)


def has_track_access(user, track, organization=None):
    return has_resource_access(user=user, resource_type=AccessService.RESOURCE_TRACK, resource=track, organization=organization)


def has_exam_access(user, exam, organization=None):
    return has_resource_access(user=user, resource_type=AccessService.RESOURCE_EXAM, resource=exam, organization=organization)


def user_has_course_access(user, course, organization=None):
    return has_course_access(user=user, course=course, organization=organization)


def has_active_track_subscription(user, track, organization=None):
    return has_track_access(user=user, track=track, organization=organization)


def can_access_exam(user, exam, organization=None):
    """Return whether the user can start an exam through a valid parent product."""
    if not user or not user.is_authenticated:
        return False, "Login required"
    if not exam.is_published:
        return False, "Exam is not published"

    # A legitimate direct admin/system access record remains supported for
    # migration compatibility. Normal users cannot buy or access an Exam as a
    # standalone product.
    if has_exam_access(user=user, exam=exam, organization=organization):
        return True, None

    from courses.models import CourseExam

    course_memberships = list(
        CourseExam.objects.filter(course__is_published=True, exam=exam).select_related("course")
    )
    for membership in course_memberships:
        if has_course_access(user=user, course=membership.course, organization=organization):
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
        if not has_track_access(user=user, track=track, organization=organization):
            continue
        locked, reason = track_exam_lock(user=user, exam=exam, track=track)
        if not locked:
            return True, None
        if reason:
            continue

    if not course_memberships and not memberships:
        return False, "This exam is not included in a Course or Track."
    return False, "Subscription required"
