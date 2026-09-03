from courses.models import Lesson, LessonProgress


def get_course_progress(user, course):
    """
    Returns (completed_count, total_count, percentage)
    """
    lessons = Lesson.objects.filter(section__course=course)
    total = lessons.count()

    if total == 0:
        return 0, 0, 0

    completed = LessonProgress.objects.filter(
        user=user,
        lesson__in=lessons,
        completed=True,
    ).count()

    percentage = int((completed / total) * 100)
    return completed, total, percentage


def _course_lessons(lesson):
    return list(
        Lesson.objects.filter(
            section__course=lesson.section.course
        ).order_by("section__order", "order")
    )


def is_lesson_unlocked(user, lesson):
    """
    A lesson is unlocked if it is the first lesson in the course
    or the previous lesson is completed.
    """
    lessons = _course_lessons(lesson)

    try:
        index = lessons.index(lesson)
    except ValueError:
        return False

    if index == 0:
        return True

    previous_lesson = lessons[index - 1]

    return LessonProgress.objects.filter(
        user=user,
        lesson=previous_lesson,
        completed=True,
    ).exists()


def get_resume_lesson(user, course):
    """
    Returns the first incomplete lesson, or the first lesson when
    the course is already complete.
    """
    completed_ids = LessonProgress.objects.filter(
        user=user,
        completed=True,
        lesson__section__course=course,
    ).values_list("lesson_id", flat=True)

    lesson = (
        Lesson.objects
        .filter(section__course=course)
        .exclude(id__in=completed_ids)
        .order_by("section__order", "order")
        .first()
    )

    if lesson:
        return lesson

    return (
        Lesson.objects
        .filter(section__course=course)
        .order_by("section__order", "order")
        .first()
    )


def get_next_lesson(lesson):
    """Return the next lesson in course order, or None."""
    lessons = _course_lessons(lesson)

    try:
        index = lessons.index(lesson)
    except ValueError:
        return None

    if index + 1 < len(lessons):
        return lessons[index + 1]

    return None


def get_previous_lesson(lesson):
    """Return the previous lesson in course order, or None."""
    lessons = _course_lessons(lesson)

    try:
        index = lessons.index(lesson)
    except ValueError:
        return None

    if index > 0:
        return lessons[index - 1]

    return None
