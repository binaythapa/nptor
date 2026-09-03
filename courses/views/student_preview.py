from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from courses.models import Course


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
        },
    )
