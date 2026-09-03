# quiz/services/access.py

from subscriptions.services import AccessService
from quiz.models import UserExam


# ============================================================
# GENERIC RESOURCE ACCESS
# ============================================================

def has_resource_access(
    user,
    resource_type,
    resource,
    organization=None,
):
    """
    Central access check for Course / Track / Exam.

    AccessService is the single source of truth.

    Returns:
        True  -> access allowed
        False -> access denied
    """

    if not user or not user.is_authenticated:
        return False

    if not resource:
        return False

    # --------------------------------------------------------
    # Current AccessService API
    # --------------------------------------------------------
    #
    # AccessService.has_access() currently expects:
    #
    #     student
    #     resource_type
    #     resource
    #
    # It does not currently accept organization.
    #
    # Keep organization in this wrapper for backward
    # compatibility with existing callers.
    # --------------------------------------------------------

    return AccessService.has_access(
        student=user,
        resource_type=resource_type,
        resource=resource,
    )


# ============================================================
# COURSE ACCESS
# ============================================================

def has_course_access(
    user,
    course,
    organization=None,
):
    """
    Check whether a user has access to a Course.
    """

    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
        organization=organization,
    )


# ============================================================
# TRACK ACCESS
# ============================================================

def has_track_access(
    user,
    track,
    organization=None,
):
    """
    Check whether a user has access to an ExamTrack.
    """

    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_TRACK,
        resource=track,
        organization=organization,
    )


# ============================================================
# EXAM ACCESS
# ============================================================

def has_exam_access(
    user,
    exam,
    organization=None,
):
    """
    Check whether a user has direct access to an Exam.

    This checks the actual Exam ResourceAccess record.

    Track-level inheritance is handled by can_access_exam().
    """

    return has_resource_access(
        user=user,
        resource_type=AccessService.RESOURCE_EXAM,
        resource=exam,
        organization=organization,
    )


# ============================================================
# COURSE ACCESS — BACKWARD COMPATIBILITY
# ============================================================

def user_has_course_access(
    user,
    course,
    organization=None,
):
    """
    Backward-compatible wrapper.

    Existing code can continue calling:

        user_has_course_access(user, course)

    while the actual access logic lives in
    subscriptions.AccessService.
    """

    return has_course_access(
        user=user,
        course=course,
        organization=organization,
    )


# ============================================================
# TRACK ACCESS — BACKWARD COMPATIBILITY
# ============================================================

def has_active_track_subscription(
    user,
    track,
    organization=None,
):
    """
    Backward-compatible function.

    New code should use has_track_access().
    """

    return has_track_access(
        user=user,
        track=track,
        organization=organization,
    )


# ============================================================
# EXAM ACCESS
# ============================================================

def can_access_exam(
    user,
    exam,
    organization=None,
):
    """
    Determine whether a user can access an exam.

    Access rules:

        1. User must be authenticated.
        2. Exam must be published.
        3. All prerequisite exams must have a passed attempt.
        4. Free exams are accessible.
        5. Direct Exam ResourceAccess grants access.
        6. Track ResourceAccess grants access to exams
           belonging to that track.
        7. Otherwise access is denied.

    Returns:

        (True, None)

    or:

        (False, reason)
    """

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    if not user or not user.is_authenticated:
        return False, "Login required"

    # --------------------------------------------------------
    # Published exam
    # --------------------------------------------------------

    if not exam.is_published:
        return False, "Exam is not published"

    # --------------------------------------------------------
    # PREREQUISITES
    # --------------------------------------------------------
    #
    # A prerequisite is satisfied only by a submitted,
    # passed attempt owned by the current user.  Free exams,
    # direct entitlements, and track access do not bypass a
    # prerequisite requirement.
    # --------------------------------------------------------

    prerequisite_ids = list(
        exam.prerequisite_exams.values_list(
            "id",
            flat=True,
        )
    )

    if prerequisite_ids:
        passed_count = (
            UserExam.objects
            .filter(
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

    # --------------------------------------------------------
    # Free exam
    # --------------------------------------------------------

    if exam.is_free:
        return True, None

    # --------------------------------------------------------
    # DIRECT EXAM ACCESS
    # --------------------------------------------------------

    if has_exam_access(
        user=user,
        exam=exam,
        organization=organization,
    ):
        return True, None

    # --------------------------------------------------------
    # TRACK-LEVEL ACCESS
    # --------------------------------------------------------
    #
    # A user with valid Track ResourceAccess can access
    # exams belonging to that track.
    #
    # This is intentionally checked here rather than inside
    # AccessService.has_access(exam), because ResourceAccess
    # represents access to a specific resource.
    # --------------------------------------------------------

    if exam.track:

        if has_track_access(
            user=user,
            track=exam.track,
            organization=organization,
        ):
            return True, None

    # --------------------------------------------------------
    # DENIED
    # --------------------------------------------------------

    return False, "Subscription required"
