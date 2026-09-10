from django.shortcuts import render

from organizations.permissions import org_teacher_required


@org_teacher_required
def organization_workspace(request, slug):
    """Authenticated organization workspace for teaching members."""
    organization = request.organization
    return render(
        request,
        "organizations/member/workspace.html",
        {
            "organization": organization,
            "membership": request.organization_member,
        },
    )
