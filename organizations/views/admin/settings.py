from django.shortcuts import render
from organizations.permissions import org_admin_required

@org_admin_required
def org_settings(request):
    return render(
        request,
        "organizations/admin/settings.html",
        {"org": request.active_org}
    )
