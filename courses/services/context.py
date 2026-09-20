from courses.models import Lesson


def get_course_context(request):
    """Resolve course-practice context from the request or active session.

    AJAX requests commonly POST to an endpoint without carrying the original
    ``course`` and ``lesson`` query parameters. The practice view stores this
    context in the session, so completion checks must use the same context.
    """
    course_slug = request.GET.get("course") or request.session.get(
        "course_practice_course_slug"
    )
    lesson_id = request.GET.get("lesson") or request.session.get(
        "course_practice_lesson_id"
    )

    if not course_slug or not lesson_id:
        return None, None, None

    try:
        lesson = Lesson.objects.select_related(
            "section__course"
        ).get(id=lesson_id, section__course__slug=course_slug)
    except (Lesson.DoesNotExist, TypeError, ValueError):
        return None, None, None

    return course_slug, lesson, lesson.practice_threshold
