from django.shortcuts import render

from organizations.permissions import organization_required


@organization_required
def organization_workspace(request, slug):
    """Authenticated organization workspace for active organization members."""
    organization = request.organization
    return render(
        request,
        "organizations/member/workspace.html",
        {
            "organization": organization,
            "membership": request.organization_member,
        },
    )
