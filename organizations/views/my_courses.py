from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from organizations.models.assignment import ResourceAssignment
from courses.models import Course


@login_required
def my_courses(request, slug=None):
    """Show courses assigned to the current student, grouped by organization."""
    assignments = (
        ResourceAssignment.objects
        .filter(student=request.user, resource_type=ResourceAssignment.RESOURCE_COURSE, is_active=True)
        .select_related("organization", "course")
    )
    if slug:
        assignments = assignments.filter(organization__slug=slug)

    org_courses = {}
    for assignment in assignments:
        org_courses.setdefault(assignment.organization, []).append(assignment.course)

    public_courses = Course.objects.filter(owner_type="platform", is_public=True, is_published=True)
    return render(request, "organizations/my_courses.html", {"org_courses": org_courses, "public_courses": public_courses})
