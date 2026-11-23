from django.shortcuts import render

from organizations.permissions import org_student_required
from organizations.services.dashboard import get_student_overview
from organizations.services.analytics import get_student_analytics


@org_student_required
def organization_learning(request, slug):
    """
    Role-restricted dashboard for organization students.

    Enforces that students only see their own profile, assigned courses,
    learning tracks, exams, upcoming due dates, exam attempt history, and personal learning analytics.
    """
    org = request.organization
    student_data = get_student_overview(org, request.user)
    student_analytics = get_student_analytics(org, request.user)

    return render(
        request,
        "organizations/student/learning.html",
        {
            "organization": org,
            "org": org,
            "profile": getattr(org, "profile", None),
            "portal_config": getattr(org, "portal_config", None),
            "student_data": student_data,
            "analytics": student_analytics,
            "course_assignments": student_data["course_assignments"],
            "track_assignments": student_data["track_assignments"],
            "exam_assignments": student_data["exam_assignments"],
        },
    )
