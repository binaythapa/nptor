from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from organizations.models.assignment import CourseAssignment
from courses.models import Course


@login_required
def my_courses(request):
    """
    Student dashboard:
    - Courses assigned via organizations
    - Public platform courses
    """

    # ===============================
    # ORGANIZATION ASSIGNED COURSES
    # ===============================
    assignments = (
        CourseAssignment.objects
        .filter(student=request.user)
        .select_related("organization", "course")
    )

    # Group courses by organization
    org_courses = {}
    for assignment in assignments:
        org = assignment.organization
        org_courses.setdefault(org, []).append(assignment.course)

    # ===============================
    # PUBLIC PLATFORM COURSES
    # ===============================
    public_courses = Course.objects.filter(
        owner_type="platform",
        is_public=True,
        is_published=True,
    )

    return render(
        request,
        "organizations/my_courses.html",
        {
            "org_courses": org_courses,
            "public_courses": public_courses,
        }
    )
