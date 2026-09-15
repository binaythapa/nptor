from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from organizations.models import OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


def organization_workspace(request, slug):
    """Organization workspace for teaching staff and provisioned students."""
    organization = getattr(request, "organization", None)
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    if organization is None:
        raise PermissionDenied("Organization context is required.")

    membership = OrganizationMember.objects.filter(
        user=request.user,
        organization=organization,
        is_active=True,
    ).first()
    if not membership:
        raise PermissionDenied("Active organization membership is required.")

    if membership.role == OrganizationRole.STUDENT:
        student_exists = OrganizationStudent.objects.filter(
            user=request.user,
            organization=organization,
            status=OrganizationStudent.STATUS_ACTIVE,
        ).exists()
        if not student_exists:
            raise PermissionDenied("An active student profile is required.")
    elif membership.role not in OrganizationRole.teaching_roles():
        raise PermissionDenied("Organization workspace access is required.")

    return render(
        request,
        "organizations/member/workspace.html",
        {"organization": organization, "membership": membership},
    )
