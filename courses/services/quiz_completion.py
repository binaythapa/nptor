from courses.models import Lesson, LessonProgress

def handle_course_quiz_completion(request, user_exam, context):
    lesson_id = context.get("lesson_id")

    try:
        lesson = Lesson.objects.get(id=lesson_id, lesson_type="quiz")
    except Lesson.DoesNotExist:
        return

    progress, _ = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson
    )

    if progress.completed:
        return

    mode = lesson.quiz_completion_mode

    completed = False
    if mode == "attempt":
        completed = True
    elif mode == "pass":
        completed = user_exam.passed is True
    elif mode == "score":
        completed = (
            user_exam.score is not None
            and user_exam.score >= lesson.quiz_min_score
        )

    if completed:
        progress.mark_completed()
