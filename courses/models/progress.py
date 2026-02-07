from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from ckeditor.fields import RichTextField

from quiz.models import *
from .lesson import *




# =====================================================
# LESSON PROGRESS
# =====================================================
class LessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_lesson_progress"
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records"
    )

    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    video_seconds_watched = models.PositiveIntegerField(default=0)
    video_duration = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "lesson")

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()

    def can_mark_complete(self):
        if not self.video_duration:
            return self.video_seconds_watched >= 300
        return (self.video_seconds_watched / self.video_duration) >= 0.9


    def __str__(self):
        return f"{self.user} → {self.lesson}"
