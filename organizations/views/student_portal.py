from django.shortcuts import render

from organizations.permissions import org_student_required
from organizations.services.dashboard import get_student_overview


@org_student_required
def organization_learning(request, slug):
    """
    Role-restricted dashboard for organization students.

    Enforces that students only see their own profile, assigned courses,
    learning tracks, exams, upcoming due dates, and exam attempt history.
    """
    org = request.organization
    student_data = get_student_overview(org, request.user)

    return render(
        request,
        "organizations/student/learning.html",
        {
            "organization": org,
            "org": org,
            "profile": getattr(org, "profile", None),
            "portal_config": getattr(org, "portal_config", None),
            "student_data": student_data,
            "course_assignments": student_data["course_assignments"],
            "track_assignments": student_data["track_assignments"],
            "exam_assignments": student_data["exam_assignments"],
        },
    )
