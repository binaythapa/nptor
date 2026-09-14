from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404

from courses.models import Course
from subscriptions.services import AccessService
from subscriptions.services.plan_service import get_plan_for_course


def is_course_free(course):
    """Return True when the course has no active paid plan."""
    plan = get_plan_for_course(course)
    return plan is None or plan.price <= 0


@login_required
def course_preview(request, slug):
    """Show the public preview or route assigned organization students to learning."""
    course = get_object_or_404(
        Course.objects.select_related("organization").prefetch_related("sections__lessons"),
        slug=slug,
    )

    # Organization-owned courses are never public marketplace products.
    # An assigned student should enter the course directly; payment/subscription
    # checks must not be involved in this path.
    if course.organization_id is not None:
        has_access = AccessService.has_course_access(request.user, course)
        if not has_access:
            raise Http404("Course not found.")
        return redirect("courses:course_detail", slug=course.slug)

    # Public course preview remains restricted to the public catalog contract.
    if not (
        course.approval_status == Course.APPROVAL_APPROVED
        and course.is_published
        and course.is_public
        and course.category_id is not None
        and course.category.is_active
        and course.category.organization_id is None
        and course.category.domain_id is not None
        and course.category.domain.is_active
        and course.category.domain.organization_id is None
    ):
        raise Http404("Course not found.")

    sections = list(course.sections.all())
    first_lesson = next(
        (lesson for section in sections for lesson in section.lessons.all()),
        None,
    )

    return render(
        request,
        "courses/student/course_preview.html",
        {
            "course": course,
            "preview_lesson": first_lesson,
            "sections": sections,
            "is_free": is_course_free(course),
        },
    )
