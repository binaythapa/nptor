from django.shortcuts import render
from organizations.permissions import org_admin_required
from courses.models import Course
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from organizations.permissions import org_admin_required
from organizations.models.subscription import OrganizationCourseSubscription
from courses.models import Course


@org_admin_required
def org_courses(request):
    courses = Course.objects.filter(
        organization=request.active_org
    )

    return render(
        request,
        "organizations/admin/courses.html",
        {"courses": courses}
    )


@org_admin_required
def org_courses(request):
    org = request.active_org

    # All published platform courses
    all_courses = Course.objects.filter(
        is_published=True,
        owner_type="platform"
    ).order_by("title")

    # Courses already attached to org
    attached_course_ids = set(
        OrganizationCourseSubscription.objects.filter(
            organization=org,
            is_active=True
        ).values_list("course_id", flat=True)
    )

    courses = [
        {
            "course": course,
            "is_attached": course.id in attached_course_ids,
        }
        for course in all_courses
    ]

    return render(
        request,
        "organizations/admin/courses/list.html",
        {"courses": courses}
    )


@org_admin_required
def org_course_attach(request, course_id):
    org = request.active_org
    course = get_object_or_404(Course, id=course_id, is_published=True)

    OrganizationCourseSubscription.objects.get_or_create(
        organization=org,
        course=course,
        defaults={"is_active": True}
    )

    messages.success(request, f"{course.title} attached to organization.")
    return redirect("organizations_admin:courses")


@org_admin_required
def org_course_detach(request, course_id):
    org = request.active_org

    sub = OrganizationCourseSubscription.objects.filter(
        organization=org,
        course_id=course_id
    ).first()

    if sub:
        sub.delete()
        messages.success(request, "Course detached successfully.")

    return redirect("organizations_admin:courses")
