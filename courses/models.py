from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from ckeditor.fields import RichTextField

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

    thumbnail = models.ImageField(
        upload_to="courses/",
        null=True,
        blank=True
    )

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

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()

    def can_mark_complete(self):
        if not self.video_duration:
            return self.video_seconds_watched >= 30
        return (self.video_seconds_watched / self.video_duration) >= 0.2


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

    def __str__(self):
        return f"Certificate → {self.user} | {self.course}"
