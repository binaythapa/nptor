from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from ckeditor_uploader.fields import RichTextUploadingField

from .category import Category
from .managers import QuestionQuerySet


class Question(models.Model):
    """
    Master Question Bank.

    A question has:
        - one optional primary category
        - zero or more additional categories

    This supports multi-category exam blueprints while
    retaining a clear primary classification.
    """

    objects = QuestionQuerySet.as_manager()

    # =========================================================
    # QUESTION TYPES
    # =========================================================

    SINGLE = "single"
    MULTI = "multi"
    TRUE_FALSE = "tf"
    DROPDOWN = "dropdown"
    FILL_BLANK = "fill"
    NUMERIC = "numeric"
    MATCHING = "match"
    ORDERING = "order"

    QUESTION_TYPES = (
        (SINGLE, "Single Choice"),
        (MULTI, "Multiple Choice"),
        (TRUE_FALSE, "True / False"),
        (DROPDOWN, "Dropdown"),
        (FILL_BLANK, "Fill in the Blank"),
        (NUMERIC, "Numeric"),
        (MATCHING, "Matching"),
        (ORDERING, "Ordering"),
    )

    # =========================================================
    # DIFFICULTY
    # =========================================================

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    DIFFICULTY_CHOICES = (
        (EASY, "Easy"),
        (MEDIUM, "Medium"),
        (HARD, "Hard"),
    )

    # =========================================================
    # CORE / OWNERSHIP
    # =========================================================

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questions",
        help_text="Organization that owns this question.",
    )

    # =========================================================
    # PRIMARY CATEGORY
    # =========================================================

    primary_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_questions",
        help_text=(
            "Primary category used for the question's "
            "main classification."
        ),
    )

    # =========================================================
    # MULTI-CATEGORY CLASSIFICATION
    # =========================================================

    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="questions",
        help_text=(
            "All categories associated with this question. "
            "A question may belong to multiple categories."
        ),
    )

    # =========================================================
    # QUESTION CONFIGURATION
    # =========================================================

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default=SINGLE,
    )

    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # =========================================================
    # QUESTION CONTENT
    # =========================================================

    text = RichTextUploadingField(
        help_text="Question text",
    )

    explanation = RichTextUploadingField(
        blank=True,
        null=True,
        help_text="Explanation shown after answer submission.",
    )

    # =========================================================
    # FILL IN BLANK
    # =========================================================

    correct_text = models.TextField(
        blank=True,
        null=True,
    )

    # =========================================================
    # NUMERIC QUESTION
    # =========================================================

    numeric_answer = models.FloatField(
        blank=True,
        null=True,
    )

    numeric_tolerance = models.FloatField(
        default=0,
    )

    # =========================================================
    # MATCHING
    # =========================================================

    matching_pairs = models.JSONField(
        blank=True,
        null=True,
    )

    # =========================================================
    # ORDERING
    # =========================================================

    ordering_items = models.JSONField(
        blank=True,
        null=True,
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

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_updated",
    )

    # =========================================================
    # SOFT DELETE
    # =========================================================

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions_deleted",
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [           
            models.Index(
                fields=[
                    "primary_category",
                    "is_active",
                    "is_deleted",
                ],
                name="q_primary_cat_active_idx",
            ),


            models.Index(
                fields=[
                    "organization",
                    "is_active",
                    "is_deleted",
                ],
                name="question_org_active_idx",
            ),
            models.Index(
                fields=[
                    "difficulty",
                    "is_active",
                    "is_deleted",
                ],
                name="question_difficulty_active_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        # -----------------------------------------------------
        # Soft-delete consistency
        # -----------------------------------------------------

        if self.is_active and self.is_deleted:
            raise ValidationError(
                "A deleted question cannot be active."
            )

        # -----------------------------------------------------
        # Numeric validation
        # -----------------------------------------------------

        if self.numeric_tolerance < 0:
            raise ValidationError({
                "numeric_tolerance": (
                    "Numeric tolerance cannot be negative."
                )
            })

        if (
            self.question_type == self.NUMERIC
            and self.numeric_answer is None
        ):
            raise ValidationError({
                "numeric_answer": (
                    "Numeric answer is required for "
                    "numeric questions."
                )
            })

        # -----------------------------------------------------
        # Fill-in-the-blank validation
        # -----------------------------------------------------

        if (
            self.question_type == self.FILL_BLANK
            and not self.correct_text
        ):
            raise ValidationError({
                "correct_text": (
                    "Correct text is required for "
                    "fill-in-the-blank questions."
                )
            })

    # =========================================================
    # TEMPORARY BACKWARD-COMPATIBILITY ALIAS
    # =========================================================

    @property
    def category(self):
        """
        Temporary Python-level compatibility alias.

        IMPORTANT:
        This is NOT a Django model field.

        New code should use:

            question.primary_category

        instead of:

            question.category
        """

        return self.primary_category

    @category.setter
    def category(self, value):
        """
        Temporary Python-level compatibility assignment.
        """

        self.primary_category = value

    # =========================================================
    # CATEGORY HELPERS
    # =========================================================

    def get_all_categories(self):
        """
        Return all categories associated with this question.

        The primary category is automatically included in
        the returned queryset even if it is not present in
        the M2M categories relationship.
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
            return Category.objects.none()

        return Category.objects.filter(
            id__in=category_ids,
        )

    def has_category(self, category):
        """
        Check whether this question belongs to a category.
        """

        if not category:
            return False

        if self.primary_category_id == category.id:
            return True

        return self.categories.filter(
            id=category.id,
        ).exists()

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        text = self.text or ""

        return (
            text[:75] + "..."
            if len(text) > 75
            else text
        )