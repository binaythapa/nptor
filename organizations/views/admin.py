from django.shortcuts import render
from organizations.permissions import org_admin_required
from organizations.models import (
    OrganizationMember,
    CourseAssignment,
    CourseAccess,
)
from courses.models import Course
from organizations.models.membership import OrganizationMember
from organizations.models.organization import *



@org_admin_required
def org_dashboard(request):
    org = request.active_org

    stats = {
        "students": OrganizationMember.objects.filter(
            organization=org, role="student", is_active=True
        ).count(),
        "courses": Course.objects.filter(
            organization=org, is_published=True
        ).count(),
        "assignments": CourseAssignment.objects.filter(
            organization=org
        ).count(),
    }

    return render(request, "organizations/admin/dashboard.html", {
        "org": org,
        "stats": stats,
    })


@org_admin_required
def org_courses(request):
    courses = Course.objects.filter(organization=request.active_org)
    return render(request, "organizations/admin/courses.html", {
        "courses": courses,
    })


@org_admin_required
def org_students(request):
    members = OrganizationMember.objects.filter(
        organization=request.active_org
    ).select_related("user")

    return render(request, "organizations/admin/students.html", {
        "members": members,
    })


@org_admin_required
def org_assignments(request):
    assignments = CourseAssignment.objects.filter(
        organization=request.active_org
    ).select_related("student", "course")

    return render(request, "organizations/admin/assignments.html", {
        "assignments": assignments,
    })


@org_admin_required
def org_settings(request):
    return render(request, "organizations/admin/settings.html", {
        "org": request.active_org,
    })
