from django.shortcuts import render

from organizations.permissions import org_teacher_required
from organizations.services.dashboard import get_teacher_overview


@org_teacher_required
def org_teacher_dashboard(request, slug):
    """
    Role-restricted dashboard for organization teaching staff.

    Enforces that teachers only see academic sections they are assigned to,
    student counts within those sections only, section-level resource assignments,
    and assignments they have created.
    """
    org = request.organization
    teacher_data = get_teacher_overview(org, request.user)
    return render(
        request,
        "organizations/admin/teacher_dashboard.html",
        {
            "org": org,
            "teacher_data": teacher_data,
        },
    )
