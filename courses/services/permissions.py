# ============================================================
# COURSE PERMISSIONS
# ============================================================

from functools import wraps

from django.http import HttpResponseForbidden

from organizations.models.role import OrganizationRole
from organizations.permissions import get_active_membership


def can_edit_course(user, course):
    """
    Determine whether a user can edit a course.

    Rules:
        1. Superuser can edit any course.
        2. Creator can edit a platform course they created.
        3. Organization courses require active membership in
           that organization with a teaching/content role.

    An organization course must never be editable solely because
    the requester is its creator; organization membership is the
    authoritative boundary for organization-owned content.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not course.organization:
        return course.created_by == user

    membership = get_active_membership(
        user,
        course.organization,
    )

    if not membership:
        return False

    return membership.role in OrganizationRole.teaching_roles()


def can_create_course(user, organization=None):
    """
    Determine whether a user may create a course.

    Platform courses are restricted to platform administrators.
    Organization courses require active membership in the target
    organization with a teaching/content role.

    The active organization is a routing/context value, not an
    authorization grant; callers must pass it through this helper.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not organization:
        return False

    membership = get_active_membership(
        user,
        organization,
    )

    if not membership:
        return False

    return membership.role in OrganizationRole.teaching_roles()


def can_preview_course(user, course):
    """
    Determine whether a user can preview a course that is not
    publicly available yet.

    Platform creators can preview their own platform courses.
    Organization courses require the same active teaching-role
    boundary as editing; creator status alone is not sufficient.
    Platform administrators can preview any course.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    if not course.organization:
        return course.created_by == user

    membership = get_active_membership(
        user,
        course.organization,
    )

    if not membership:
        return False

    return membership.role in OrganizationRole.teaching_roles()


def can_view_instructor_dashboard(user, organization):
    """
    Determine whether a user may view organization-specific
    instructor dashboard data.

    Organization course and student-progress information is
    restricted to active teaching/content roles. A normal student
    must never gain access merely because middleware selected the
    organization as their active organization.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not organization:
        return False

    membership = get_active_membership(
        user,
        organization,
    )

    if not membership:
        return False

    return membership.role in OrganizationRole.teaching_roles()


def instructor_dashboard_access_required(view_func):
    """Require an active teaching role for organization dashboard data."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        organization = getattr(request, "active_org", None)

        if organization:
            if not can_view_instructor_dashboard(
                request.user,
                organization,
            ):
                return HttpResponseForbidden(
                    "You are not allowed to view organization instructor data."
                )

            # instructor_dashboard historically reads request.organization.
            # Populate it only after the centralized authorization succeeds.
            request.organization = organization

        return view_func(request, *args, **kwargs)

    return wrapped


# ============================================================
# COURSE REVIEW PERMISSION
# ============================================================


def can_review_course(user, course):
    """
    Determine whether a user can review a course.

    Only platform administrators can currently
    review courses.
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
    """

    if not user or not user.is_authenticated:
        return False

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
    """Determine whether an administrator can request changes."""

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
    """Determine whether an administrator can approve a course."""

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
    """Determine whether an administrator can reject a course."""

    if not can_review_course(
        user,
        course,
    ):
        return False

    return (
        course.approval_status
        == course.APPROVAL_PENDING
    )
