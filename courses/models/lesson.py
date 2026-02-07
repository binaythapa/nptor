from django.db import models
from .section import *


# =====================================================
# LESSON
# =====================================================

class Lesson(models.Model):

    TYPE_VIDEO = "video"
    TYPE_ARTICLE = "article"
    TYPE_QUIZ = "quiz"
    TYPE_PRACTICE = "practice"

    LESSON_TYPES = [
        (TYPE_VIDEO, "Video"),
        (TYPE_ARTICLE, "Article"),
        (TYPE_QUIZ, "Quiz"),
        (TYPE_PRACTICE, "Practice"),
    ]

    section = models.ForeignKey(
        CourseSection,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES)
    order = models.PositiveIntegerField()

    # ================= CONTENT =================
    video_url = models.URLField(blank=True, null=True)

    # 🎯 Rich content with inline images, code, diagrams
    article_content = RichTextField(
        blank=True,
        help_text="Supports text, images, code blocks, diagrams"
    )

    # ================= PRACTICE =================
    practice_domain = models.ForeignKey(
        Domain,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    practice_category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_practice_lessons"
    )

    practice_difficulty = models.CharField(
        max_length=20,
        choices=(
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard"),
        ),
        null=True,
        blank=True,
        help_text="Optional difficulty filter when practice is launched from course"
    )  

    practice_threshold = models.PositiveIntegerField(default=10)
    practice_lock_filters = models.BooleanField(default=True)
    practice_require_correct = models.BooleanField(default=False)

    practice_min_accuracy = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # ================= QUIZ =================
    exam = models.ForeignKey(
        Exam,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_lessons"
    )

    quiz_completion_mode = models.CharField(
        max_length=20,
        choices=[
            ("attempt", "Any attempt"),
            ("pass", "Must pass"),
            ("score", "Minimum score"),
        ],
        default="attempt"
    )

    quiz_min_score = models.PositiveIntegerField(default=0)
    quiz_allow_mock = models.BooleanField(default=False)
    quiz_max_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    # ================= VALIDATION =================
    def clean(self):

        if self.lesson_type == self.TYPE_QUIZ and not self.exam:
            raise ValidationError("Quiz lesson must be linked to an exam.")

        if self.lesson_type == self.TYPE_PRACTICE:
            if not self.practice_domain or not self.practice_category:
                raise ValidationError("Practice lessons require domain and category.")

            if self.practice_category.domain != self.practice_domain:
                raise ValidationError("Category must belong to selected domain.")

            if self.practice_threshold <= 0:
                raise ValidationError("Practice threshold must be greater than 0.")

        if self.lesson_type != self.TYPE_PRACTICE:
            if self.practice_domain or self.practice_category:
                raise ValidationError("Practice fields only allowed for practice lessons.")

    def __str__(self):
        return f"{self.section.course.title} → {self.title}"

