from django.core.exceptions import ValidationError
from django.db import models


class Exam(models.Model):
    """Represents an independent assessment that can be reused in tracks."""

    title = models.CharField(max_length=255)

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="exams",
    )

    primary_category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_exams",
        help_text="Primary category used for the exam's main classification.",
    )

    categories = models.ManyToManyField(
        "Category",
        blank=True,
        related_name="exams",
        help_text="All categories covered by this exam.",
    )

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

    is_published = models.BooleanField(default=False, db_index=True)

    max_mock_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of mock attempts allowed. Use 0 to disable mock attempts.",
    )

    allow_review = models.BooleanField(
        default=True,
        help_text="If enabled, students can review answers before final submission.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "is_published"],
                name="exam_org_pub_idx",
            ),
            models.Index(
                fields=["primary_category", "is_published"],
                name="exam_primary_cat_idx",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}

        if self.question_count <= 0:
            errors["question_count"] = "Question count must be greater than zero."
        if self.duration_seconds <= 0:
            errors["duration_seconds"] = "Exam duration must be greater than zero."
        if not 0 <= self.passing_score <= 100:
            errors["passing_score"] = "Passing score must be between 0 and 100."
        if self.level <= 0:
            errors["level"] = "Exam level must be greater than zero."
        if self.max_mock_attempts < 0:
            errors["max_mock_attempts"] = "Mock attempts cannot be negative."

        if (
            self.organization_id
            and self.primary_category_id
            and self.primary_category.organization_id
            and self.primary_category.organization_id != self.organization_id
        ):
            errors["primary_category"] = (
                "Primary category must belong to the same organization as the exam."
            )

        if self.primary_category_id and not self.primary_category.is_active:
            errors["primary_category"] = (
                "An inactive category cannot be the primary category of an exam."
            )

        if errors:
            raise ValidationError(errors)

    def get_all_categories(self):
        category_ids = set(self.categories.values_list("id", flat=True))
        if self.primary_category_id:
            category_ids.add(self.primary_category_id)
        if not category_ids:
            return self.categories.none()
        return self.categories.model.objects.filter(id__in=category_ids)

    def has_category(self, category):
        if not category:
            return False
        if self.primary_category_id == category.id:
            return True
        return self.categories.filter(id=category.id).exists()

    def has_blueprint(self):
        return self.allocations.exists()

    def get_allocations(self):
        return self.allocations.select_related("category").all()

    def is_practice_mode(self):
        return self.allow_review is True

    def is_certification_mode(self):
        return self.allow_review is False

    def __str__(self):
        return self.title
