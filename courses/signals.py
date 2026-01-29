from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from quiz.models import UserExam
from .models import Lesson, LessonProgress


@receiver(post_save, sender=UserExam)
def mark_quiz_lesson_completed(sender, instance, **kwargs):
    if instance.status != UserExam.STATUS_SUBMITTED:
        return

    lesson = Lesson.objects.filter(exam=instance.exam).first()
    if not lesson:
        return

    LessonProgress.objects.update_or_create(
        user=instance.user,
        lesson=lesson,
        defaults={
            "completed": True,
            "completed_at": timezone.now()
        }
    )
