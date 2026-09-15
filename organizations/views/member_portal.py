from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from organizations.models import OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole
from organizations.permissions import org_teacher_required


@org_teacher_required
def _staff_workspace(request, slug):
    organization = request.organization
    return render(
        request,
        "organizations/member/workspace.html",
        {
            "organization": organization,
            "membership": request.organization_member,
        },
    )


def organization_workspace(request, slug):
    """Organization workspace for teaching staff and provisioned students."""
    organization = request.organization
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication is required.")

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
        return render(
            request,
            "organizations/member/workspace.html",
            {"organization": organization, "membership": membership},
        )

    if membership.role not in OrganizationRole.teaching_roles():
        raise PermissionDenied("Organization workspace access is required.")
    return _staff_workspace(request, slug)
