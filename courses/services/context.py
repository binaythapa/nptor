from courses.models import Lesson


def get_course_context(request):
    """Resolve course-practice context from request parameters or session.

    AJAX requests may omit the original query string. In that case, recover
    the active lesson from the session and derive its course slug directly
    from the database.
    """
    course_slug = request.GET.get("course") or request.session.get(
        "course_practice_course_slug"
    )
    lesson_id = request.GET.get("lesson") or request.session.get(
        "course_practice_lesson_id"
    )

    if not lesson_id:
        return None, None, None

    try:
        lesson = Lesson.objects.select_related(
            "section__course"
        ).get(id=lesson_id)
    except (Lesson.DoesNotExist, TypeError, ValueError):
        return None, None, None

    resolved_course_slug = lesson.section.course.slug
    if course_slug and course_slug != resolved_course_slug:
        return None, None, None

    return resolved_course_slug, lesson, lesson.practice_threshold
