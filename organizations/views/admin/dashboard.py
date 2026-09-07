from django.shortcuts import render

from organizations.permissions import org_admin_required
from organizations.services.dashboard import get_overview


@org_admin_required
def org_dashboard(request, slug):
    org = request.organization
    overview = get_overview(org)
    return render(
        request,
        "organizations/admin/dashboard.html",
        {"org": org, "stats": overview, "overview": overview},
    )
