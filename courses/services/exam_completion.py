from django.utils import timezone
from courses.models import Lesson, LessonProgress
from quiz.models import UserExam


def handle_exam_completion(request, user_exam, lesson_id):
    """
    Marks lesson completed based on configured rules.
    """
    lesson = Lesson.objects.filter(
        id=lesson_id,
        exam=user_exam.exam
    ).first()

    if not lesson:
        return

    # RULE: PASS REQUIRED
    if lesson.quiz_completion_rule == "pass":
        if user_exam.passed:
            LessonProgress.objects.update_or_create(
                user=request.user,
                lesson=lesson,
                defaults={
                    "completed": True,
                    "completed_at": timezone.now()
                }
            )

    # RULE: ATTEMPTS BASED
    elif lesson.quiz_completion_rule == "attempts":
        attempts = UserExam.objects.filter(
            user=request.user,
            exam=user_exam.exam,
            submitted_at__isnull=False
        ).count()

        if attempts >= lesson.quiz_attempt_threshold:
            LessonProgress.objects.update_or_create(
                user=request.user,
                lesson=lesson,
                defaults={
                    "completed": True,
                    "completed_at": timezone.now()
                }
            )
