from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from quiz.models import *


# =====================================================
# COURSE
# =====================================================

class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    thumbnail = models.ImageField(upload_to="courses/", null=True, blank=True)

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ]
    )

    subscription_plans = models.ManyToManyField(
        SubscriptionPlan,
        blank=True,
        related_name="course_access_courses"
    )

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# =====================================================
# COURSE SECTION
# =====================================================

class CourseSection(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.title} → {self.title}"


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


    section = models.ForeignKey(
        CourseSection,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES)
    order = models.PositiveIntegerField()

    # ---------------- CONTENT ----------------
    video_url = models.URLField(blank=True, null=True)
    article_content = models.TextField(blank=True)

    # ---------------- QUIZ ----------------
    exam = models.ForeignKey(
        Exam,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_lessons"
    )

    # ---------------- PRACTICE ----------------
    practice_domain = models.ForeignKey(
        Domain,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Domain for course-linked practice"
    )


    practice_category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_practice_lessons"
    )

    # 🎯 PRACTICE CONFIG (NEW)
    practice_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Number of questions to practice before lesson is marked completed"
    )

    practice_lock_filters = models.BooleanField(
        default=True,
        help_text="Lock domain/category filters when practice is launched from course"
    )

    practice_require_correct = models.BooleanField(
        default=False,
        help_text="Require correct answers to count toward threshold"
    )

    # (optional future)
    practice_min_accuracy = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional minimum accuracy % to complete practice lesson"
    )

    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    def clean(self):
        """
        Industry-grade validation for Lesson configuration
        """

        # ================= QUIZ =================
        if self.lesson_type == self.TYPE_QUIZ:
            if not self.exam:
                raise ValidationError(
                    {"exam": "Quiz lesson must be linked to an Exam."}
                )

        # ================= PRACTICE =================
        if self.lesson_type == self.TYPE_PRACTICE:
            if not self.practice_domain:
                raise ValidationError(
                    {"practice_domain": "Practice lesson must have a domain."}
                )

            if not self.practice_category:
                raise ValidationError(
                    {"practice_category": "Practice lesson must be linked to a category."}
                )

            if self.practice_category.domain != self.practice_domain:
                raise ValidationError(
                    {
                        "practice_category": (
                            "Selected category does not belong to the selected domain."
                        )
                    }
                )

            if self.practice_threshold <= 0:
                raise ValidationError(
                    {
                        "practice_threshold": (
                            "Practice threshold must be greater than 0."
                        )
                    }
                )

        # ================= NON-PRACTICE =================
        if self.lesson_type != self.TYPE_PRACTICE:
            if self.practice_domain or self.practice_category:
                raise ValidationError(
                    "Practice fields should only be set for Practice lessons."
                )


    

    def __str__(self):
        return f"{self.section.course.title} → {self.title}"



# =====================================================
# COURSE ENROLLMENT
# =====================================================

class CourseEnrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_enrollments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "course")
        indexes = [
            models.Index(fields=["user", "course"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.course}"


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
        indexes = [
            models.Index(fields=["user", "lesson"]),
            models.Index(fields=["completed"]),
        ]

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=["completed", "completed_at"])

    def can_mark_complete(self):
        if self.lesson.lesson_type != "video":
            return True
        if self.video_duration <= 0:
            return False
        return (self.video_seconds_watched / self.video_duration) >= 0.9

    def __str__(self):
        return f"{self.user} → {self.lesson}"


# =====================================================
# COURSE CERTIFICATE
# =====================================================

class CourseCertificate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_certificates"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates"
    )

    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_id = models.CharField(max_length=50, unique=True)

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Certificate: {self.user} → {self.course}"
