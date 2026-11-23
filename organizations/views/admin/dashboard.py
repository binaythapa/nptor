from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from organizations.models.role import OrganizationRole
from organizations.permissions import org_admin_required, organization_required
from organizations.services.dashboard import get_overview
from organizations.services.analytics import get_admin_analytics


@org_admin_required
def org_dashboard(request, slug):
    """
    Organization Owner / Admin Dashboard.

    Displays high-level KPI metrics across students, teaching staff, administrators,
    academic structure, learning products, assignment states, institutional analytics,
    and recent audit activity.
    """
    org = request.organization
    date_range = request.GET.get("range", "30d")
    overview = get_overview(org)
    analytics = get_admin_analytics(org, date_range=date_range)
    return render(
        request,
        "organizations/admin/dashboard.html",
        {
            "org": org,
            "stats": overview,
            "overview": overview,
            "analytics": analytics,
            "active_range": analytics["active_range"],
            "academic_year_count": overview["academic_years"],
            "academic_class_count": overview["classes"],
            "academic_section_count": overview["sections"],
        },
    )


@organization_required
def org_dashboard_dispatch(request, slug):
    """
    Role-aware central dashboard landing dispatcher.

    Routes users based on active organization membership role:
      - Owner / Admin -> Admin Dashboard (organizations_admin:dashboard)
      - Staff / Teacher -> Teacher Dashboard (organizations_admin:teacher_dashboard)
      - Student -> Student Dashboard (organizations_public:learning)
      - Inactive or non-member -> 403 Forbidden
    """
    member = request.organization_member
    if not member or not member.is_active:
        raise PermissionDenied("You are not an active member of this organization.")

    if member.role in OrganizationRole.administrative_roles():
        return redirect("organizations_admin:dashboard", slug=slug)
    elif member.role == OrganizationRole.STAFF:
        return redirect("organizations_admin:teacher_dashboard", slug=slug)
    elif member.role == OrganizationRole.STUDENT:
        return redirect("organizations_public:learning", slug=slug)
    else:
        raise PermissionDenied("Unrecognized organization role.")
