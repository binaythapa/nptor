from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from organizations.models import OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole
from organizations.permissions import org_staff_required


@org_staff_required
def organization_workspace(request, slug):
    """Operational organization workspace for staff/teachers."""
    organization = request.organization
    return render(
        request,
        "organizations/member/workspace.html",
        {
            "organization": organization,
            "membership": request.organization_member,
        },
    )


def student_workspace(request, slug):
    """Student workspace for an active, provisioned organization student."""
    organization = request.organization
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication is required.")
    membership = OrganizationMember.objects.filter(
        user=request.user,
        organization=organization,
        role=OrganizationRole.STUDENT,
        is_active=True,
    ).first()
    if not membership or not OrganizationStudent.objects.filter(
        user=request.user,
        organization=organization,
        status=OrganizationStudent.STATUS_ACTIVE,
    ).exists():
        raise PermissionDenied("An active student profile is required.")
    return render(
        request,
        "organizations/member/workspace.html",
        {
            "organization": organization,
            "membership": membership,
        },
    )
