from courses.models import Lesson, LessonProgress


def get_course_progress(user, course):
    """
    Returns (completed_count, total_count, percentage).
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


def _course_lessons(course):
    return Lesson.objects.filter(
        section__course=course,
    ).order_by("section__order", "order")


def is_lesson_unlocked(user, lesson):
    """
    A lesson is unlocked if it is the first lesson in the course
    or the previous lesson has been completed.
    """
    lessons = list(_course_lessons(lesson.section.course))

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
    Returns the first incomplete lesson, otherwise the first lesson.
    """
    completed_ids = LessonProgress.objects.filter(
        user=user,
        completed=True,
        lesson__section__course=course,
    ).values_list("lesson_id", flat=True)

    lesson = (
        _course_lessons(course)
        .exclude(id__in=completed_ids)
        .first()
    )

    if lesson:
        return lesson

    return _course_lessons(course).first()


def get_next_lesson(lesson):
    """
    Returns the physically next lesson in course order, or None.
    """
    lessons = list(_course_lessons(lesson.section.course))

    try:
        index = lessons.index(lesson)
    except ValueError:
        return None

    if index + 1 < len(lessons):
        return lessons[index + 1]

    return None


def get_next_learning_lesson(user, course, lesson):
    """
    Return the best next destination for a learner.

    Preference order:
    1. First incomplete lesson after the current lesson.
    2. First incomplete lesson in the course (when reviewing an older lesson).
    3. None when the whole course is complete.

    This keeps the player useful when students revisit completed lessons
    without sending them through already-completed content again.
    """
    lessons = list(_course_lessons(course))
    if not lessons:
        return None

    completed_ids = set(
        LessonProgress.objects.filter(
            user=user,
            completed=True,
            lesson__section__course=course,
        ).values_list("lesson_id", flat=True)
    )

    try:
        current_index = lessons.index(lesson)
    except ValueError:
        current_index = -1

    for candidate in lessons[current_index + 1:]:
        if candidate.id not in completed_ids:
            return candidate

    for candidate in lessons:
        if candidate.id not in completed_ids:
            return candidate

    return None
