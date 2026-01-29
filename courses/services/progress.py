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
        completed=True
    ).count()

    percentage = int((completed / total) * 100)

    return completed, total, percentage



from courses.models import Lesson, LessonProgress
def is_lesson_unlocked(user, lesson):
    """
    A lesson is unlocked if:
    - it is the first lesson in the course
    - OR the previous lesson is completed
    """

    lessons = list(
        Lesson.objects.filter(
            section__course=lesson.section.course
        ).order_by("section__order", "order")
    )

    try:
        index = lessons.index(lesson)
    except ValueError:
        return False  # lesson not part of course

    # First lesson always unlocked
    if index == 0:
        return True

    previous_lesson = lessons[index - 1]

    return LessonProgress.objects.filter(
        user=user,
        lesson=previous_lesson,
        completed=True
    ).exists()


from courses.models import Lesson, LessonProgress

from courses.models import Lesson, LessonProgress

def get_resume_lesson(user, course):
    """
    Returns:
    - First incomplete lesson if exists
    - Otherwise FIRST lesson of the course
    """

    completed_ids = LessonProgress.objects.filter(
        user=user,
        completed=True,
        lesson__section__course=course
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
    """
    Returns the next lesson in course order, or None
    """
    lessons = list(
        Lesson.objects.filter(
            section__course=lesson.section.course
        ).order_by("section__order", "order")
    )

    try:
        index = lessons.index(lesson)
    except ValueError:
        return None

    if index + 1 < len(lessons):
        return lessons[index + 1]

    return None
