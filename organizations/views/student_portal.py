from django.shortcuts import render

from organizations.models.assignment import ResourceAssignment
from organizations.permissions import org_student_required


@org_student_required
def organization_learning(request, slug):
    organization = request.organization
    assignments = (
        ResourceAssignment.objects
        .filter(organization=organization, student=request.user, active=True)
        .select_related("course", "track", "exam")
        .order_by("due_at", "-created_at")
    )
    course_assignments = [a for a in assignments if a.resource_type == ResourceAssignment.TYPE_COURSE and a.course]
    track_assignments = [a for a in assignments if a.resource_type == ResourceAssignment.TYPE_TRACK and a.track]
    exam_assignments = [a for a in assignments if a.resource_type == ResourceAssignment.TYPE_EXAM and a.exam]
    return render(
        request,
        "organizations/student/learning.html",
        {
            "organization": organization,
            "profile": organization.profile,
            "portal_config": organization.portal_config,
            "course_assignments": course_assignments,
            "track_assignments": track_assignments,
            "exam_assignments": exam_assignments,
        },
    )
