from django.shortcuts import render

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
