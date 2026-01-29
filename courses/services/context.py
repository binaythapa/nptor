from courses.models import Lesson

def get_course_context(request):
    course_slug = request.GET.get("course")
    lesson_id = request.GET.get("lesson")

    if not course_slug or not lesson_id:
        return None, None, None

    try:
        lesson = Lesson.objects.select_related(
            "section__course"
        ).get(id=lesson_id, section__course__slug=course_slug)
    except Lesson.DoesNotExist:
        return None, None, None

    return course_slug, lesson, lesson.practice_threshold
