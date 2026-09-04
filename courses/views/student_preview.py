from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from courses.models import Course
from subscriptions.services.plan_service import get_plan_for_course


def is_course_free(course):
    """Return True when the course has no active paid plan."""
    plan = get_plan_for_course(course)
    return plan is None or plan.price <= 0


@login_required
def course_preview(request, slug):
    course = get_object_or_404(
        Course.objects.filter(
            approval_status=Course.APPROVAL_APPROVED,
            is_published=True,
            is_public=True,
            organization__isnull=True,
            category__is_active=True,
            category__organization__isnull=True,
            category__domain__is_active=True,
            category__domain__organization__isnull=True,
        ).prefetch_related("sections__lessons"),
        slug=slug,
    )

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
