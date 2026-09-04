from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from courses.models import Course, CourseEnrollment
from organizations.models import ResourceAccess
from subscriptions.services.plan_service import get_plan_for_course


def is_course_free(course):
    """Return True when the course has no active paid plan."""
    plan = get_plan_for_course(course)
    return plan is None or plan.price <= 0


@login_required
@require_POST
def enroll_free_course(request, slug):
    """Enroll the current student in a publicly available free course."""
    course = get_object_or_404(
        Course,
        slug=slug,
        approval_status=Course.APPROVAL_APPROVED,
        is_published=True,
        is_public=True,
    )

    if not is_course_free(course):
        raise Http404("This course requires paid access.")

    enrollment, _ = CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={"is_active": True},
    )

    if not enrollment.is_active:
        enrollment.is_active = True
        enrollment.save(update_fields=["is_active"])

    ResourceAccess.objects.get_or_create(
        user=request.user,
        resource_type=ResourceAccess.RESOURCE_COURSE,
        course=course,
        source=ResourceAccess.SOURCE_PUBLIC,
        defaults={
            "is_active": True,
        },
    )

    return redirect("courses:course_learn", slug=course.slug)
