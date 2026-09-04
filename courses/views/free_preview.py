from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from courses.models import Course, Lesson
from subscriptions.services.access_service import AccessService
from subscriptions.services.plan_service import get_plan_for_course
from courses.utils import youtube_embed_url

FREE_PREVIEW_LESSON_COUNT = 3


def _course_requires_paid_access(course):
    plan = get_plan_for_course(course, None)
    return plan is not None and plan.price > 0


def _public_course(slug):
    return get_object_or_404(
        Course.objects.select_related("created_by", "organization"),
        slug=slug,
        approval_status=Course.APPROVAL_APPROVED,
        is_published=True,
        is_public=True,
    )


@login_required
def course_free_preview(request, slug, lesson_id=None):
    """Render the public three-lesson preview for a paid course."""
    course = _public_course(slug)

    if not _course_requires_paid_access(course):
        raise Http404("Free courses do not require preview mode.")

    has_access = AccessService.has_access(
        student=request.user,
        resource_type=AccessService.RESOURCE_COURSE,
        resource=course,
    )
    if has_access:
        raise Http404("Course preview is only for users without course access.")

    lessons = list(
        Lesson.objects.filter(section__course=course)
        .select_related("section")
        .order_by("section__order", "order")
    )
    preview_lessons = lessons[:FREE_PREVIEW_LESSON_COUNT]

    lesson = None
    preview_locked = False
    if lesson_id is None:
        lesson = preview_lessons[0] if preview_lessons else None
    else:
        lesson = next((item for item in lessons if item.id == lesson_id), None)
        if lesson is None:
            raise Http404("Lesson not found.")
        preview_locked = lesson not in preview_lessons
        if preview_locked:
            lesson = None

    next_lesson = None
    if lesson:
        try:
            index = preview_lessons.index(lesson)
        except ValueError:
            index = -1
        if index >= 0 and index + 1 < len(preview_lessons):
            next_lesson = preview_lessons[index + 1]

    video_embed_url = None
    if lesson and lesson.lesson_type == Lesson.TYPE_VIDEO:
        video_embed_url = youtube_embed_url(lesson.video_url)

    return render(
        request,
        "courses/student/course_free_preview.html",
        {
            "course": course,
            "sections": course.sections.prefetch_related("lessons").order_by("order"),
            "lesson": lesson,
            "next_lesson": next_lesson,
            "preview_lessons": preview_lessons,
            "preview_locked": preview_locked,
            "is_free_preview": bool(lesson) and not preview_locked,
            "free_preview_count": FREE_PREVIEW_LESSON_COUNT,
            "total": len(lessons),
            "progress": 0,
            "completed_lesson_ids": set(),
            "lesson_progress": None,
            "video_embed_url": video_embed_url,
        },
    )
