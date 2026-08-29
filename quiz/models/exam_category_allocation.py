from django.core.exceptions import ValidationError
from django.db import models


class ExamCategoryAllocation(models.Model):
    """
    Defines the question-selection blueprint for an Exam.

    An exam can distribute questions across multiple categories.

    Example - percentage based:

        Architecture     20%
        Security          20%
        Compute           30%
        Storage            30%

    Example - fixed count:

        Architecture     10 questions
        Security          10 questions
        Compute           15 questions
        Storage           15 questions

    An allocation must use exactly one of:

        percentage
        fixed_count
    """

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.CASCADE,
        related_name="exam_allocations",
    )

    # =========================================================
    # ALLOCATION
    # =========================================================

    percentage = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Percentage of exam questions allocated to this "
            "category. Use either percentage or fixed count."
        ),
    )

    fixed_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Exact number of questions allocated to this "
            "category. Use either fixed count or percentage."
        ),
    )

    # =========================================================
    # OPTIONS
    # =========================================================

    include_descendants = models.BooleanField(
        default=True,
        help_text=(
            "If enabled, questions from child categories "
            "are also eligible for this allocation."
        ),
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = [
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "exam",
                    "category",
                ],
                name="unique_exam_category_alloc",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "exam",
                    "category",
                ],
                name="exam_cat_alloc_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        errors = {}

        has_percentage = (
            self.percentage is not None
        )

        has_fixed_count = (
            self.fixed_count is not None
        )

        # -----------------------------------------------------
        # Exactly one allocation method
        # -----------------------------------------------------

        if (
            has_percentage
            and has_fixed_count
        ):
            errors["percentage"] = (
                "Use either percentage or fixed count, "
                "not both."
            )

        elif not has_percentage and not has_fixed_count:
            errors["percentage"] = (
                "Either percentage or fixed count "
                "is required."
            )

        # -----------------------------------------------------
        # Percentage
        # -----------------------------------------------------

        if has_percentage:

            if self.percentage <= 0:
                errors["percentage"] = (
                    "Percentage must be greater than 0."
                )

            elif self.percentage > 100:
                errors["percentage"] = (
                    "Percentage cannot exceed 100."
                )

        # -----------------------------------------------------
        # Fixed count
        # -----------------------------------------------------

        if has_fixed_count:

            if self.fixed_count <= 0:
                errors["fixed_count"] = (
                    "Fixed question count must be "
                    "greater than 0."
                )

        # -----------------------------------------------------
        # Exam validation
        # -----------------------------------------------------

        if self.exam_id:

            if (
                self.exam.question_count is not None
                and self.exam.question_count <= 0
            ):
                errors["exam"] = (
                    "Exam question count must be greater "
                    "than zero."
                )

        # -----------------------------------------------------
        # Category validation
        # -----------------------------------------------------

        if (
            self.exam_id
            and self.category_id
        ):

            # Prevent assigning an inactive category
            # to an exam blueprint.
            if not self.category.is_active:
                errors["category"] = (
                    "An inactive category cannot be "
                    "used in an exam allocation."
                )

        if errors:
            raise ValidationError(errors)

    # =========================================================
    # ALLOCATION TYPE
    # =========================================================

    @property
    def allocation_type(self):
        if self.fixed_count is not None:
            return "fixed"

        if self.percentage is not None:
            return "percentage"

        return None

    # =========================================================
    # QUESTION COUNT
    # =========================================================

    def get_question_count(
        self,
        total_questions,
    ):
        """
        Return the number of questions this allocation
        contributes to an exam.

        Fixed:

            10 -> 10

        Percentage:

            50 questions * 20% = 10
        """

        if total_questions <= 0:
            return 0

        if self.fixed_count is not None:
            return self.fixed_count

        if self.percentage is not None:
            return int(
                total_questions
                * self.percentage
                / 100
            )

        return 0

    # =========================================================
    # CATEGORY IDS
    # =========================================================

    def get_category_ids(self):
        """
        Return the category IDs that should participate
        in question selection.

        When include_descendants=True:

            Parent
              ├── Child A
              ├── Child B
              └── Child C

        all categories are included.
        """

        if not self.category_id:
            return []

        if not self.include_descendants:
            return [
                self.category_id,
            ]

        return (
            self.category
            .get_descendants_include_self()
        )

    # =========================================================
    # DISPLAY
    # =========================================================

    def __str__(self):

        if self.fixed_count is not None:

            allocation = (
                f"{self.fixed_count} questions"
            )

        elif self.percentage is not None:

            allocation = (
                f"{self.percentage}%"
            )

        else:

            allocation = "undefined"

        return (
            f"{self.exam} → "
            f"{self.category} → "
            f"{allocation}"
        )