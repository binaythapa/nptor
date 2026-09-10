from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Exam(models.Model):
    """Represents a reusable exam definition.

    Track-specific sequencing and prerequisites live on ``TrackExam``. Pricing
    is represented by subscription plans rather than being stored on the exam
    itself, so one exam can be reused by multiple tracks and products.
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

    # =========================================================
    # ACCESS / PRICING PLANS
    # =========================================================

    subscription_plans = models.ManyToManyField(
        "subscriptions.SubscriptionPlan",
        blank=True,
        related_name="exams",
        help_text="Optional plans that grant direct access to this exam.",
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
            "Primary category used for the exam's main classification."
        ),
    )

    # =========================================================
    # MULTI-CATEGORY CLASSIFICATION
    # =========================================================

    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="exams",
        help_text="All categories covered by this exam.",
    )

    # =========================================================
    # EXAM CONFIGURATION
    # =========================================================

    question_count = models.PositiveIntegerField(
        default=10,
        help_text="Total number of questions in the exam.",
    )

    duration_seconds = models.PositiveIntegerField(
        help_text="Maximum exam duration in seconds.",
    )

    level = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text="Difficulty/level of this exam.",
    )

    passing_score = models.FloatField(
        default=50.0,
        help_text="Minimum percentage required to pass.",
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
            "Maximum number of mock attempts allowed. Use 0 to disable mock attempts."
        ),
    )

    # =========================================================
    # REVIEW / CERTIFICATION
    # =========================================================

    allow_review = models.BooleanField(
        default=True,
        help_text="If enabled, students can review answers before final submission.",
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
        related_name="exams_created",
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
                    "primary_category",
                    "is_published",
                ],
                name="exam_primary_cat_idx",
            ),
        ]

    def __init__(self, *args, **kwargs):
        """Accept the legacy exam pricing arguments during the data-model transition.

        Older integrations/tests constructed exams with ``track``, ``price``,
        ``currency`` and ``is_free`` fields. Those fields are no longer stored
        on ``Exam``; subscription plans are the source of truth. Keeping these
        values in memory prevents old callers from failing at model construction
        while allowing new persisted records to use the current schema.
        """
        self._legacy_track = kwargs.pop("track", None)
        self._legacy_price = kwargs.pop("price", None)
        self._legacy_currency = kwargs.pop("currency", None)
        self._legacy_is_free = kwargs.pop("is_free", None)
        super().__init__(*args, **kwargs)

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        errors = {}

        if self.duration_seconds <= 0:
            errors["duration_seconds"] = "Duration must be greater than zero."

        if self.question_count <= 0:
            errors["question_count"] = "Question count must be greater than zero."

        if not 0 <= self.passing_score <= 100:
            errors["passing_score"] = "Passing score must be between 0 and 100."

        if self.organization_id is None and self.is_published:
            errors["is_published"] = "Platform exams must be managed through the platform publishing workflow."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title
