# courses/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from quiz.models import UserExam

from .models import Lesson, LessonProgress


# ============================================================
# QUIZ LESSON COMPLETION
# ============================================================

@receiver(
    post_save,
    sender=UserExam,
)
def mark_quiz_lesson_completed(
    sender,
    instance,
    **kwargs,
):
    """
    Automatically mark the corresponding course quiz lesson
    as completed when the user submits the exam.

    Flow:

        UserExam submitted
              ↓
        Find Course Lesson
              ↓
        Mark LessonProgress completed
    """

    # --------------------------------------------------------
    # Only process submitted exams
    # --------------------------------------------------------

    if instance.status != UserExam.STATUS_SUBMITTED:
        return

    # --------------------------------------------------------
    # Find course lesson associated with this exam
    # --------------------------------------------------------

    lesson = (
        Lesson.objects
        .filter(
            exam=instance.exam,
        )
        .first()
    )

    if not lesson:
        return

    # --------------------------------------------------------
    # Mark lesson completed
    # --------------------------------------------------------

    LessonProgress.objects.update_or_create(
        user=instance.user,
        lesson=lesson,
        defaults={
            "completed": True,
            "completed_at": timezone.now(),
        },
    )