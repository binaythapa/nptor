from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from organizations.models.membership import OrganizationMember


@login_required
def switch_organization(request, org_id):
    membership = OrganizationMember.objects.filter(
        user=request.user,
        organization_id=org_id,
        is_active=True
    ).first()

    if membership:
        request.session["active_org_id"] = org_id

    return redirect("dashboard")  # update if needed
