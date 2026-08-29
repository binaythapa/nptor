# organizations/permissions.py

"""
Organization authorization layer.

Responsibilities:
    - Authentication checks
    - Organization resolution
    - Active membership resolution
    - Organization role authorization
    - Organization capability authorization
    - Platform administrator authorization

Important architectural rule:

    This module must remain independent of application-specific
    business logic.

It should NOT import:
    - courses
    - quiz
    - subscriptions
    - payments

Resource-specific authorization belongs in the relevant service layer.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole


# ============================================================
# INTERNAL HELPERS
# ============================================================


def _login_redirect():
    """
    Return the application's login redirect.
    """

    return redirect(
        "accounts:request-login-otp"
    )


def get_active_membership(user, organization):
    """
    Return the user's active membership in the organization.

    Returns None when:
        - user is not authenticated
        - organization is unavailable
        - user is not an active member
    """

    if not user or not user.is_authenticated:
        return None

    if not organization:
        return None

    return (
        OrganizationMember.objects
        .select_related(
            "user",
            "organization",
        )
        .filter(
            user=user,
            organization=organization,
            is_active=True,
        )
        .first()
    )


def user_has_role(user, organization, roles):
    """
    Return True when the user has one of the supplied roles
    in the specified organization.

    Organization membership is ALWAYS required.

    Django's global:
        is_staff
        is_superuser

    do not automatically grant organization-level access.
    """

    member = get_active_membership(
        user,
        organization,
    )

    if not member:
        return False

    if isinstance(roles, str):
        roles = {roles}

    return member.role in set(roles)


# ============================================================
# ROLE CHECKS
# ============================================================


def user_is_organization_owner(user, organization):
    """
    Return True when the user is an active organization owner.
    """

    return user_has_role(
        user,
        organization,
        {
            OrganizationRole.ORG_OWNER,
        },
    )


def user_is_organization_admin(user, organization):
    """
    Return True when the user is an active organization
    owner or administrator.
    """

    return user_has_role(
        user,
        organization,
        OrganizationRole.administrative_roles(),
    )


def user_is_staff(user, organization):
    """
    Return True when the user is an active organization
    staff/teacher member.
    """

    return user_has_role(
        user,
        organization,
        {
            OrganizationRole.STAFF,
        },
    )


def user_is_teacher(user, organization):
    """
    Return True when the user belongs to a role capable of
    teaching/content operations.

    Current teaching roles:

        - Organization Owner
        - Organization Admin
        - Staff / Teacher
    """

    return user_has_role(
        user,
        organization,
        OrganizationRole.teaching_roles(),
    )


def user_is_student(user, organization):
    """
    Return True when the user is an active organization student.
    """

    return user_has_role(
        user,
        organization,
        {
            OrganizationRole.STUDENT,
        },
    )


# ============================================================
# CAPABILITY CHECKS
# ============================================================


def user_can_manage_organization(user, organization):
    """
    Organization-level administration.

    Allowed:
        - Owner
        - Admin

    Not allowed:
        - Staff
        - Student
    """

    return user_is_organization_admin(
        user,
        organization,
    )


def user_can_manage_users(user, organization):
    """
    Manage organization memberships and users.

    Allowed:
        - Owner
        - Admin
    """

    return user_is_organization_admin(
        user,
        organization,
    )


def user_can_manage_students(user, organization):
    """
    Manage students within the organization.

    Allowed:
        - Owner
        - Admin
        - Staff / Teacher
    """

    return user_is_teacher(
        user,
        organization,
    )


def user_can_manage_content(user, organization):
    """
    Manage organization learning content.

    Allowed:
        - Owner
        - Admin
        - Staff / Teacher

    Resource-specific ownership and access rules must still
    be checked by the relevant service layer.
    """

    return user_is_teacher(
        user,
        organization,
    )


def user_can_create_courses(user, organization):
    """
    Determine whether a user may create organization courses.

    Allowed:
        - Owner
        - Admin
        - Staff / Teacher
    """

    return user_is_teacher(
        user,
        organization,
    )


def user_can_assign_resources(user, organization):
    """
    Determine whether a user may assign courses, tracks,
    or exams to organization students.

    Allowed:
        - Owner
        - Admin
        - Staff / Teacher
    """

    return user_is_teacher(
        user,
        organization,
    )


def user_can_view_student_progress(user, organization):
    """
    Determine whether a user may view student progress.

    Allowed:
        - Owner
        - Admin
        - Staff / Teacher

    The service/view layer should additionally restrict the
    exact students/resources visible to a teacher.
    """

    return user_is_teacher(
        user,
        organization,
    )


def user_can_manage_billing(user, organization):
    """
    Determine whether a user may manage organization billing,
    subscriptions, or organization purchases.

    Allowed:
        - Owner
        - Admin
    """

    return user_is_organization_admin(
        user,
        organization,
    )


# ============================================================
# ORGANIZATION CONTEXT DECORATOR
# ============================================================


def organization_required(view_func):
    """
    Require:

        1. Authentication
        2. Valid active organization
        3. Active organization membership

    The organization is resolved from:

        /organization/<slug>/...

    The following are attached to request:

        request.organization
        request.active_org
        request.organization_member
    """

    @wraps(view_func)
    def _wrapped(
        request,
        slug,
        *args,
        **kwargs,
    ):

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        if not request.user.is_authenticated:
            return _login_redirect()

        # ----------------------------------------------------
        # Organization
        # ----------------------------------------------------

        organization = get_object_or_404(
            Organization,
            slug=slug,
            is_active=True,
        )

        # ----------------------------------------------------
        # Membership
        # ----------------------------------------------------

        member = get_active_membership(
            request.user,
            organization,
        )

        if not member:
            raise PermissionDenied(
                "You are not a member of this organization."
            )

        # ----------------------------------------------------
        # Request context
        # ----------------------------------------------------

        request.organization = organization
        request.active_org = organization
        request.organization_member = member

        return view_func(
            request,
            slug,
            *args,
            **kwargs,
        )

    return _wrapped


# ============================================================
# GENERIC ORGANIZATION ROLE DECORATOR
# ============================================================


def organization_role_required(*required_roles):
    """
    Require one of the supplied organization roles.

    Example:

        @organization_role_required(
            OrganizationRole.ORG_OWNER,
            OrganizationRole.ORG_ADMIN,
        )

    Organization must be supplied through the URL:

        /organization/<slug>/...

    The following are attached to request:

        request.organization
        request.active_org
        request.organization_member
    """

    if not required_roles:
        raise ValueError(
            "At least one organization role is required."
        )

    required_roles = set(
        required_roles
    )

    valid_roles = set(
        OrganizationRole.all_roles()
    )

    invalid_roles = (
        required_roles - valid_roles
    )

    if invalid_roles:
        raise ValueError(
            "Invalid organization role(s): "
            f"{', '.join(sorted(invalid_roles))}"
        )

    def decorator(view_func):

        @wraps(view_func)
        def _wrapped(
            request,
            slug,
            *args,
            **kwargs,
        ):

            # ------------------------------------------------
            # Authentication
            # ------------------------------------------------

            if not request.user.is_authenticated:
                return _login_redirect()

            # ------------------------------------------------
            # Organization
            # ------------------------------------------------

            organization = get_object_or_404(
                Organization,
                slug=slug,
                is_active=True,
            )

            # ------------------------------------------------
            # Membership
            # ------------------------------------------------

            member = get_active_membership(
                request.user,
                organization,
            )

            if not member:
                raise PermissionDenied(
                    "You are not a member of this organization."
                )

            # ------------------------------------------------
            # Role
            # ------------------------------------------------

            if member.role not in required_roles:
                raise PermissionDenied(
                    "You do not have permission to access "
                    "this organization resource."
                )

            # ------------------------------------------------
            # Request context
            # ------------------------------------------------

            request.organization = organization
            request.active_org = organization
            request.organization_member = member

            return view_func(
                request,
                slug,
                *args,
                **kwargs,
            )

        return _wrapped

    return decorator


# ============================================================
# ORGANIZATION OWNER
# ============================================================


def org_owner_required(view_func):
    """
    Organization owner only.
    """

    return organization_role_required(
        OrganizationRole.ORG_OWNER,
    )(view_func)


# ============================================================
# ORGANIZATION ADMIN
# ============================================================


def org_admin_required(view_func):
    """
    Organization owner or administrator.

    Kept under the existing function name for backward
    compatibility.

    Existing views using:

        @org_admin_required

    continue to work.
    """

    return organization_role_required(
        OrganizationRole.ORG_OWNER,
        OrganizationRole.ORG_ADMIN,
    )(view_func)


# ============================================================
# STAFF / TEACHER
# ============================================================


def org_staff_required(view_func):
    """
    Staff / teacher only.

    Organization owners and admins are intentionally excluded.
    Use org_teacher_required when administrative roles should
    also be permitted.
    """

    return organization_role_required(
        OrganizationRole.STAFF,
    )(view_func)


# ============================================================
# TEACHING ACCESS
# ============================================================


def org_teacher_required(view_func):
    """
    Require teaching/content capability.

    Allowed:

        - Organization Owner
        - Organization Admin
        - Staff / Teacher

    Intended for:

        - Creating courses
        - Managing permitted courses
        - Creating learning content
        - Assigning resources
        - Viewing permitted student progress

    Resource ownership and detailed authorization must still
    be enforced by the relevant service layer.
    """

    return organization_role_required(
        *OrganizationRole.teaching_roles(),
    )(view_func)


# ============================================================
# STUDENT
# ============================================================


def org_student_required(view_func):
    """
    Organization student only.
    """

    return organization_role_required(
        OrganizationRole.STUDENT,
    )(view_func)


# ============================================================
# PLATFORM ADMIN
# ============================================================


def platform_admin_required(view_func):
    """
    Require platform-level Django staff access.

    Platform administrators are separate from organization
    administrators.

    Platform administrator:

        request.user.is_staff == True

    Organization administrator:

        OrganizationMember.role in:
            ORG_OWNER
            ORG_ADMIN
    """

    @wraps(view_func)
    def _wrapped(
        request,
        *args,
        **kwargs,
    ):

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        if not request.user.is_authenticated:
            return _login_redirect()

        # ----------------------------------------------------
        # Platform administrator
        # ----------------------------------------------------

        if not request.user.is_staff:
            raise PermissionDenied(
                "Platform administrator access required."
            )

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return _wrapped