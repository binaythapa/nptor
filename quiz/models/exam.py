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
    # CORE
    # =====================================================

    title = models.CharField(
        max_length=255
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

    duration_seconds = models.PositiveIntegerField()

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
        help_text="If checked, this exam is free",
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required only if exam is paid",
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

    # =====================================================
    # MOCK EXAM
    # =====================================================

    max_mock_attempts = models.PositiveIntegerField(
        default=3,
        help_text=(
            "Number of mock attempts allowed for this exam "
            "(0 = no mock)"
        ),
    )

    # =====================================================
    # REVIEW / CERTIFICATION BEHAVIOR
    # =====================================================

    allow_review = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, students can review answers "
            "before final submission."
        ),
    )

    # =====================================================
    # BEHAVIOR HELPERS
    # =====================================================

    def is_practice_mode(self):
        """
        Exam allows answer review.
        """
        return self.allow_review is True

    def is_certification_mode(self):
        """
        Exam does not allow answer review.
        """
        return self.allow_review is False

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.title