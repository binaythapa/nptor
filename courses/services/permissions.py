# ============================================================
# COURSE PERMISSIONS
# ============================================================


def can_edit_course(user, course):
    """
    Determine whether a user can edit a course.

    Rules:
        1. Superuser can edit any course.
        2. Course creator can edit their own course.
        3. Organization user can edit courses belonging
           to their organization.
    """

    if not user or not user.is_authenticated:
        return False

    # --------------------------------------------------------
    # PLATFORM ADMIN
    # --------------------------------------------------------

    if user.is_superuser:
        return True

    # --------------------------------------------------------
    # COURSE CREATOR
    # --------------------------------------------------------

    if course.created_by == user:
        return True

    # --------------------------------------------------------
    # ORGANIZATION USER
    # --------------------------------------------------------

    if (
        course.organization
        and hasattr(user, "organization")
        and user.organization
    ):
        return (
            course.organization
            == user.organization
        )

    return False


# ============================================================
# COURSE REVIEW PERMISSION
# ============================================================

def can_review_course(user, course):
    """
    Determine whether a user can review a course.

    Only platform administrators can currently
    review courses.

    Organization instructors/creators must NOT
    be able to approve their own courses.
    """

    if not user or not user.is_authenticated:
        return False

    return user.is_superuser


# ============================================================
# COURSE PUBLISH PERMISSION
# ============================================================

def can_publish_course(user, course):
    """
    Determine whether a user can publish a course.

    Rules:
        1. User must be authenticated.
        2. Course must already be approved.
        3. Only platform administrators can publish.
    """

    if not user or not user.is_authenticated:
        return False

    if not course.is_approved():
        return False

    return user.is_superuser


# ============================================================
# COURSE SUBMISSION PERMISSION
# ============================================================

def can_submit_course_for_review(user, course):
    """
    Determine whether a user can submit a course
    for administrator review.

    Allowed states:

        DRAFT
        CHANGES_REQUIRED
        REJECTED

    Not allowed:

        PENDING
        APPROVED
    """

    if not user or not user.is_authenticated:
        return False

    # User must have permission to edit the course.
    if not can_edit_course(
        user,
        course,
    ):
        return False

    return course.approval_status in (
        course.APPROVAL_DRAFT,
        course.APPROVAL_CHANGES,
        course.APPROVAL_REJECTED,
    )


# ============================================================
# REQUEST CHANGES
# ============================================================

def can_request_changes(user, course):
    """
    Determine whether an administrator can request
    changes to a course.

    Course must currently be pending review.
    """

    if not can_review_course(
        user,
        course,
    ):
        return False

    return (
        course.approval_status
        == course.APPROVAL_PENDING
    )


# ============================================================
# APPROVE COURSE
# ============================================================

def can_approve_course(user, course):
    """
    Determine whether an administrator can approve
    a course currently awaiting review.
    """

    if not can_review_course(
        user,
        course,
    ):
        return False

    return (
        course.approval_status
        == course.APPROVAL_PENDING
    )


# ============================================================
# REJECT COURSE
# ============================================================

def can_reject_course(user, course):
    """
    Determine whether an administrator can reject
    a course currently awaiting review.
    """

    if not can_review_course(
        user,
        course,
    ):
        return False

    return (
        course.approval_status
        == course.APPROVAL_PENDING
    )