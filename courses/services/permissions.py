# ============================================================
# COURSE PERMISSIONS
# ============================================================

from functools import wraps

from django.http import HttpResponseForbidden

from organizations.models.role import OrganizationRole
from organizations.permissions import get_active_membership


def _approval_status(course, name, default):
    """Read a course approval constant while supporting lightweight test doubles."""
    return getattr(course, name, default)


def can_edit_course(user, course):
    """
    Determine whether a user can edit course content.

    Only draft, changes-required, and rejected courses are mutable.
    Organization owners/admins may modify organization courses; staff
    may modify only organization courses they created. Platform courses
    remain restricted to platform administrators.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    editable_states = (
        _approval_status(course, "APPROVAL_DRAFT", "draft"),
        _approval_status(course, "APPROVAL_CHANGES", "changes_required"),
        _approval_status(course, "APPROVAL_REJECTED", "rejected"),
    )
    if course.approval_status not in editable_states:
        return False

    if not course.organization:
        return course.created_by == user

    membership = get_active_membership(
        user,
        course.organization,
    )

    if not membership:
        return False

    if membership.role in OrganizationRole.administrative_roles():
        return True

    return (
        membership.role == OrganizationRole.STAFF
        and course.created_by_id == user.id
    )


# Backwards-compatible name used by older callers and security tests.
def can_modify_course_content(user, course):
    return can_edit_course(user, course)


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


def course_creation_access_required(view_func):
    """Require platform-admin or active organization teaching access."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        organization = getattr(request, "active_org", None)

        if organization is None:
            organization = getattr(request, "organization", None)

        if not can_create_course(request.user, organization):
            return HttpResponseForbidden(
                "You are not allowed to create courses."
            )

        request.organization = organization

        return view_func(request, *args, **kwargs)

    return wrapped


def can_preview_course(user, course):
    """
    Determine whether a user can preview a course that is not
    publicly available yet.
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
    """Determine whether a user may view organization instructor data."""

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

            request.organization = organization

        return view_func(request, *args, **kwargs)

    return wrapped


# ============================================================
# COURSE REVIEW PERMISSION
# ============================================================


def can_review_course(user, course):
    """Only platform administrators can currently review courses."""

    if not user or not user.is_authenticated:
        return False

    return user.is_superuser


# ============================================================
# COURSE PUBLISH PERMISSION
# ============================================================


def can_publish_course(user, course):
    """Determine whether a user can publish a course."""

    if not user or not user.is_authenticated:
        return False

    if not course.is_approved():
        return False

    return user.is_superuser


# ============================================================
# COURSE SUBMISSION PERMISSION
# ============================================================


def can_submit_course_for_review(user, course):
    """Determine whether a user can submit a course for review."""

    if not user or not user.is_authenticated:
        return False

    if not can_edit_course(
        user,
        course,
    ):
        return False

    return course.approval_status in (
        _approval_status(course, "APPROVAL_DRAFT", "draft"),
        _approval_status(course, "APPROVAL_CHANGES", "changes_required"),
        _approval_status(course, "APPROVAL_REJECTED", "rejected"),
    )


# ============================================================
# REQUEST CHANGES
# ============================================================


def can_request_changes(user, course):
    """Determine whether an administrator can request changes."""

    if not can_review_course(user, course):
        return False

    return course.approval_status == _approval_status(
        course, "APPROVAL_PENDING", "pending"
    )


# ============================================================
# APPROVE COURSE
# ============================================================


def can_approve_course(user, course):
    """Determine whether an administrator can approve a course."""

    if not can_review_course(user, course):
        return False

    return course.approval_status == _approval_status(
        course, "APPROVAL_PENDING", "pending"
    )


# ============================================================
# REJECT COURSE
# ============================================================


def can_reject_course(user, course):
    """Determine whether an administrator can reject a course."""

    if not can_review_course(user, course):
        return False

    return course.approval_status == _approval_status(
        course, "APPROVAL_PENDING", "pending"
    )
