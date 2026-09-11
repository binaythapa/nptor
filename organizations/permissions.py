# organizations/permissions.py
"""Central authorization for organization and platform access."""

from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole


def _login_redirect():
    return redirect("accounts:request-login-otp")


def get_active_membership(user, organization):
    if not user or not user.is_authenticated or not organization:
        return None
    return (
        OrganizationMember.objects.select_related("user", "organization")
        .filter(user=user, organization=organization, is_active=True).first()
    )


def user_has_role(user, organization, roles):
    member = get_active_membership(user, organization)
    if not member:
        return False
    if isinstance(roles, str):
        roles = {roles}
    return member.role in set(roles)


def user_is_organization_owner(user, organization):
    return user_has_role(user, organization, {OrganizationRole.ORG_OWNER})


def user_is_organization_admin(user, organization):
    return user_has_role(user, organization, OrganizationRole.administrative_roles())


def user_is_staff(user, organization):
    return user_has_role(user, organization, {OrganizationRole.STAFF})


def user_is_teacher(user, organization):
    return user_has_role(user, organization, OrganizationRole.teaching_roles())


def user_is_student(user, organization):
    return user_has_role(user, organization, {OrganizationRole.STUDENT})


def user_can_manage_organization(user, organization):
    return user_is_organization_admin(user, organization)


def user_can_manage_users(user, organization):
    return user_is_organization_admin(user, organization)


def user_can_manage_students(user, organization):
    return user_is_teacher(user, organization)


def user_can_manage_content(user, organization):
    return user_is_teacher(user, organization)


def user_can_create_courses(user, organization):
    return user_is_teacher(user, organization)


def user_can_assign_resources(user, organization):
    return user_is_teacher(user, organization)


def user_can_view_student_progress(user, organization):
    return user_is_teacher(user, organization)


def user_can_manage_billing(user, organization):
    return user_is_organization_admin(user, organization)


def organization_required(view_func):
    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect()
        organization = get_object_or_404(Organization, slug=slug, is_active=True)
        member = get_active_membership(request.user, organization)
        if not member:
            raise PermissionDenied("You are not a member of this organization.")
        request.organization = organization
        request.active_org = organization
        request.organization_member = member
        return view_func(request, slug, *args, **kwargs)
    return _wrapped


def organization_role_required(*required_roles):
    if not required_roles:
        raise ValueError("At least one organization role is required.")
    required_roles = set(required_roles)
    invalid_roles = required_roles - set(OrganizationRole.all_roles())
    if invalid_roles:
        raise ValueError(f"Invalid organization role(s): {', '.join(sorted(invalid_roles))}")

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, slug, *args, **kwargs):
            if not request.user.is_authenticated:
                return _login_redirect()
            organization = get_object_or_404(Organization, slug=slug, is_active=True)
            member = get_active_membership(request.user, organization)
            if not member:
                raise PermissionDenied("You are not a member of this organization.")
            if member.role not in required_roles:
                raise PermissionDenied("You do not have permission to access this organization resource.")
            request.organization = organization
            request.active_org = organization
            request.organization_member = member
            return view_func(request, slug, *args, **kwargs)
        return _wrapped
    return decorator


def org_owner_required(view_func):
    return organization_role_required(OrganizationRole.ORG_OWNER)(view_func)


def org_admin_required(view_func):
    return organization_role_required(OrganizationRole.ORG_OWNER, OrganizationRole.ORG_ADMIN)(view_func)


def org_staff_required(view_func):
    return organization_role_required(OrganizationRole.STAFF)(view_func)


def org_teacher_required(view_func):
    return organization_role_required(*OrganizationRole.teaching_roles())(view_func)


def org_student_required(view_func):
    return organization_role_required(OrganizationRole.STUDENT)(view_func)


def is_platform_admin(user):
    """Return True only for an explicit platform administrator."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return bool(getattr(getattr(user, "profile", None), "is_platform_admin", False))


def platform_admin_required(view_func):
    """Require explicit platform-admin status; organization roles never grant it."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect()
        if not is_platform_admin(request.user):
            raise PermissionDenied("Platform administrator access required.")
        return view_func(request, *args, **kwargs)
    return _wrapped
