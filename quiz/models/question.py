from django.conf import settings
from django.db import models

from ckeditor_uploader.fields import RichTextUploadingField

from .category import Category
from .managers import QuestionQuerySet


class Question(models.Model):
    """
    Master Question Bank
    """

    objects = QuestionQuerySet.as_manager()

    # ==========================
    # Question Types
    # ==========================

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

    # ==========================
    # Difficulty
    # ==========================

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    DIFFICULTY_CHOICES = (
        (EASY, "Easy"),
        (MEDIUM, "Medium"),
        (HARD, "Hard"),
    )

    # ==========================
    # Core Fields
    # ==========================

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="questions",
        null=True,
        blank=True,
    )

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default=SINGLE,
    )

    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
    )

    is_active = models.BooleanField(default=True)

    # ==========================
    # Question Content
    # ==========================

    text = RichTextUploadingField(
        help_text="Question text",
    )

    explanation = RichTextUploadingField(
        blank=True,
        null=True,
        help_text="Explanation shown after answer submission.",
    )

    # ==========================
    # Fill in Blank
    # ==========================

    correct_text = models.TextField(
        blank=True,
        null=True,
    )

    # ==========================
    # Numeric Question
    # ==========================

    numeric_answer = models.FloatField(
        blank=True,
        null=True,
    )

    numeric_tolerance = models.FloatField(
        default=0,
    )

    # ==========================
    # Matching
    # ==========================

    matching_pairs = models.JSONField(
        blank=True,
        null=True,
    )

    # ==========================
    # Ordering
    # ==========================

    ordering_items = models.JSONField(
        blank=True,
        null=True,
    )

    # ==========================
    # Audit
    # ==========================

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

    # ==========================
    # Soft Delete
    # ==========================

    is_deleted = models.BooleanField(
        default=False,
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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        text = self.text or ""
        return text[:75] + "..." if len(text) > 75 else text