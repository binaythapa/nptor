from django.shortcuts import render
from organizations.permissions import org_admin_required
from organizations.models.assignment import CourseAssignment

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from organizations.permissions import org_admin_required
from organizations.models.assignment import CourseAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.subscription import OrganizationCourseSubscription
from courses.models import Course


@org_admin_required
def org_assignments(request):
    org = request.active_org

    assignments = (
        CourseAssignment.objects
        .filter(organization=org)
        .select_related("student", "course")
        .order_by("-assigned_at")
    )

    return render(
        request,
        "organizations/admin/assignments/list.html",
        {"assignments": assignments}
    )

from organizations.models.access import CourseAccess

@org_admin_required
def org_assignment_create(request):
    org = request.active_org

    # Students in org
    students = OrganizationMember.objects.filter(
        organization=org,
        role="student",
        is_active=True
    ).select_related("user")

    # Courses attached to org
    courses = Course.objects.filter(
        organization_subscriptions__organization=org,
        organization_subscriptions__is_active=True,
    )

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        course_id = request.POST.get("course_id")

        student = get_object_or_404(
            OrganizationMember,
            id=student_id,
            organization=org,
            role="student"
        )

        course = get_object_or_404(
            Course,
            id=course_id,
            organization_subscriptions__organization=org
        )

        # 1️⃣ Create course assignment
        CourseAssignment.objects.get_or_create(
            student=student.user,
            organization=org,
            course=course,
        )

        # 2️⃣ Enable course access
        access, created = CourseAccess.objects.get_or_create(
            user=student.user,
            course=course,
            source="organization",
            organization=org,
            defaults={"is_active": True},
        )

        # If access already existed but was inactive → reactivate
        if not created and not access.is_active:
            access.is_active = True
            access.save(update_fields=["is_active"])

        messages.success(
            request,
            f"{course.title} assigned to {student.user.email}"
        )

        return redirect("organizations_admin:assignments")

    return render(
        request,
        "organizations/admin/assignments/create.html",
        {
            "students": students,
            "courses": courses,
        }
    )

@org_admin_required
def org_assignment_remove(request, assignment_id):
    assignment = get_object_or_404(
        CourseAssignment,
        id=assignment_id,
        organization=request.active_org
    )

    assignment.delete()
    messages.success(request, "Assignment removed successfully.")

    return redirect("organizations_admin:assignments")
