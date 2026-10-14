from django.db import models


class Exam(models.Model):
    """
    Represents an individual exam within an ExamTrack.

    An exam can be:
    - Free or paid
    - Published or unpublished
    - Associated with one track
    - Associated with one primary category
    - Associated with multiple categories
    - Locked behind prerequisite exams
    """

    # =====================================================
    # EXAM TYPES
    # =====================================================

    class ExamType(models.TextChoices):
        NORMAL = "NORMAL", "Normal Exam"
        COURSE = "COURSE", "Course Exam"
        MOCK = "MOCK", "Mock Exam"
        ASSESSMENT = "ASSESSMENT", "Assessment"

    # =====================================================
    # CORE
    # =====================================================

    title = models.CharField(
        max_length=255,
        db_index=True,
    )

    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices,
        default=ExamType.NORMAL,
        db_index=True,
        help_text="Defines how this exam is used in the platform.",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="exams",
    )

    track = models.ForeignKey(
        "ExamTrack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_exams",
    )

    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="exams",
    )

    # =====================================================
    # EXAM CONFIGURATION
    # =====================================================

    question_count = models.PositiveIntegerField(
        default=10
    )

    duration_seconds = models.PositiveIntegerField(
        help_text="Exam duration in seconds.",
    )

    level = models.PositiveIntegerField(
        default=1,
        db_index=True,
    )

    passing_score = models.FloatField(
        default=50.0
    )

    # =====================================================
    # PREREQUISITES
    # =====================================================

    prerequisite_exams = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="unlocked_exams",
    )

    # =====================================================
    # FREE / PAID
    # =====================================================

    is_free = models.BooleanField(
        default=True,
        db_index=True,
        help_text="If enabled, students can access exam for free.",
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required only for paid exams.",
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =====================================================
    # PUBLISHING
    # =====================================================

    is_published = models.BooleanField(
        default=False,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =====================================================
    # MOCK EXAM
    # =====================================================

    max_mock_attempts = models.PositiveIntegerField(
        default=3,
        help_text=(
            "0 means mock attempts disabled."
        ),
    )

    # =====================================================
    # REVIEW / CERTIFICATION BEHAVIOR
    # =====================================================

    allow_review = models.BooleanField(
        default=True,
        help_text=(
            "Students can review answers before final submission."
        ),
    )

    # =====================================================
    # MODEL META
    # =====================================================

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["exam_type", "is_published"]),
            models.Index(fields=["organization", "exam_type"]),
            models.Index(fields=["level"]),
        ]

    # =====================================================
    # BEHAVIOR HELPERS
    # =====================================================

    @property
    def is_practice_mode(self):
        """
        Exam allows answer review.
        """
        return self.allow_review is True

    @property
    def is_certification_mode(self):
        """
        Exam does not allow answer review.
        """
        return self.allow_review is False

    @property
    def is_course_exam(self):
        return self.exam_type == self.ExamType.COURSE

    @property
    def is_normal_exam(self):
        return self.exam_type == self.ExamType.NORMAL

    @property
    def is_mock_exam(self):
        return self.exam_type == self.ExamType.MOCK

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return f"{self.title} ({self.exam_type})"