from django.shortcuts import render

from organizations.permissions import org_teacher_required
from organizations.services.dashboard import get_teacher_overview
from organizations.services.analytics import get_teacher_analytics


@org_teacher_required
def org_teacher_dashboard(request, slug):
    """
    Role-restricted dashboard for organization teaching staff.

    Enforces that teachers only see academic sections they are assigned to,
    student counts within those sections only, section-level resource assignments,
    assignments they have created, and performance analytics for their students.
    """
    org = request.organization
    date_range = request.GET.get("range", "30d")
    teacher_data = get_teacher_overview(org, request.user)
    teacher_analytics = get_teacher_analytics(org, request.user, date_range=date_range)
    return render(
        request,
        "organizations/admin/teacher_dashboard.html",
        {
            "org": org,
            "teacher_data": teacher_data,
            "analytics": teacher_analytics,
            "active_range": teacher_analytics["active_range"],
        },
    )
