from django.core.exceptions import ValidationError
from django.db import models


class Exam(models.Model):
    """
    Represents an individual exam within an ExamTrack.

    An exam supports:

    - One primary category
    - Multiple categories
    - Category-based question allocation
    - Fixed-count or percentage blueprints
    - Free or paid access
    - Prerequisite exams
    - Practice/mock/certification behavior
    - Publishing controls
    """

    # =========================================================
    # CORE
    # =========================================================

    title = models.CharField(
        max_length=255,
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

    # =========================================================
    # PRIMARY CATEGORY
    # =========================================================

    primary_category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_exams",
        help_text=(
            "Primary category used for the exam's main "
            "classification."
        ),
    )

    # =========================================================
    # MULTI-CATEGORY CLASSIFICATION
    # =========================================================

    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="exams",
        help_text=(
            "All categories covered by this exam."
        ),
    )

    # =========================================================
    # EXAM CONFIGURATION
    # =========================================================

    question_count = models.PositiveIntegerField(
        default=10,
        help_text=(
            "Total number of questions in the exam."
        ),
    )

    duration_seconds = models.PositiveIntegerField(
        help_text=(
            "Maximum exam duration in seconds."
        ),
    )

    level = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text=(
            "Difficulty/level of this exam."
        ),
    )

    passing_score = models.FloatField(
        default=50.0,
        help_text=(
            "Minimum percentage required to pass."
        ),
    )

    # =========================================================
    # PREREQUISITES
    # =========================================================

    prerequisite_exams = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="unlocked_exams",
    )

    # =========================================================
    # FREE / PAID
    # =========================================================

    is_free = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, this exam can be accessed without "
            "a paid subscription."
        ),
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Price of the exam when it is not free."
        ),
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =========================================================
    # PUBLISHING
    # =========================================================

    is_published = models.BooleanField(
        default=False,
        db_index=True,
    )

    # =========================================================
    # MOCK EXAM
    # =========================================================

    max_mock_attempts = models.PositiveIntegerField(
        default=3,
        help_text=(
            "Maximum number of mock attempts allowed. "
            "Use 0 to disable mock attempts."
        ),
    )

    # =========================================================
    # REVIEW / CERTIFICATION
    # =========================================================

    allow_review = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, students can review answers "
            "before final submission."
        ),
    )

    # =========================================================
    # AUDIT
    # =========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "is_published",
                ],
                name="exam_org_pub_idx",
            ),
            models.Index(
                fields=[
                    "track",
                    "is_published",
                ],
                name="exam_track_pub_idx",
            ),
            models.Index(
                fields=[
                    "primary_category",
                    "is_published",
                ],
                name="exam_primary_cat_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        errors = {}

        # -----------------------------------------------------
        # Question count
        # -----------------------------------------------------

        if self.question_count <= 0:
            errors["question_count"] = (
                "Question count must be greater than zero."
            )

        # -----------------------------------------------------
        # Duration
        # -----------------------------------------------------

        if self.duration_seconds <= 0:
            errors["duration_seconds"] = (
                "Exam duration must be greater than zero."
            )

        # -----------------------------------------------------
        # Passing score
        # -----------------------------------------------------

        if not 0 <= self.passing_score <= 100:
            errors["passing_score"] = (
                "Passing score must be between 0 and 100."
            )

        # -----------------------------------------------------
        # Level
        # -----------------------------------------------------

        if self.level <= 0:
            errors["level"] = (
                "Exam level must be greater than zero."
            )

        # -----------------------------------------------------
        # Mock attempts
        # -----------------------------------------------------

        if self.max_mock_attempts < 0:
            errors["max_mock_attempts"] = (
                "Mock attempts cannot be negative."
            )

        # -----------------------------------------------------
        # Paid exam
        # -----------------------------------------------------

        if not self.is_free:

            if self.price is None:
                errors["price"] = (
                    "Price is required for a paid exam."
                )

            elif self.price <= 0:
                errors["price"] = (
                    "Price must be greater than zero."
                )

        # -----------------------------------------------------
        # Free exam
        # -----------------------------------------------------

        if self.is_free and self.price is not None:
            if self.price < 0:
                errors["price"] = (
                    "Price cannot be negative."
                )

        # -----------------------------------------------------
        # Track organization consistency
        # -----------------------------------------------------

        if (
            self.organization_id
            and self.track_id
            and self.track.organization_id
            and self.track.organization_id
            != self.organization_id
        ):
            errors["track"] = (
                "Exam and track must belong to the "
                "same organization."
            )

        # -----------------------------------------------------
        # Primary category organization consistency
        # -----------------------------------------------------

        if (
            self.organization_id
            and self.primary_category_id
            and self.primary_category.organization_id
            and self.primary_category.organization_id
            != self.organization_id
        ):
            errors["primary_category"] = (
                "Primary category must belong to the "
                "same organization as the exam."
            )

        # -----------------------------------------------------
        # Primary category cannot be inactive
        # -----------------------------------------------------

        if (
            self.primary_category_id
            and not self.primary_category.is_active
        ):
            errors["primary_category"] = (
                "An inactive category cannot be the "
                "primary category of an exam."
            )

        if errors:
            raise ValidationError(errors)

    # =========================================================
    # CATEGORY HELPERS
    # =========================================================

    def get_all_categories(self):
        """
        Return all categories associated with the exam.

        The primary category is automatically included even
        if it has not yet been added to the M2M relationship.
        """

        category_ids = set(
            self.categories.values_list(
                "id",
                flat=True,
            )
        )

        if self.primary_category_id:
            category_ids.add(
                self.primary_category_id
            )

        if not category_ids:
            return self.categories.none()

        return self.categories.model.objects.filter(
            id__in=category_ids,
        )

    def has_category(self, category):
        """
        Check whether the exam belongs to a category.
        """

        if not category:
            return False

        if (
            self.primary_category_id
            == category.id
        ):
            return True

        return self.categories.filter(
            id=category.id,
        ).exists()

    # =========================================================
    # BLUEPRINT HELPERS
    # =========================================================

    def has_blueprint(self):
        """
        Return True when the exam has at least one
        category allocation.
        """

        return self.allocations.exists()

    def get_allocations(self):
        """
        Return allocations ordered by creation/order.
        """

        return self.allocations.select_related(
            "category",
        ).all()

    # =========================================================
    # EXAM MODE
    # =========================================================

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

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return self.title