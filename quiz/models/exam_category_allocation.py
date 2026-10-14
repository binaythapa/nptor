from django.core.exceptions import ValidationError
from django.db import models


class ExamCategoryAllocation(models.Model):
    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.CASCADE,
    )

    percentage = models.PositiveIntegerField(
        default=0,
    )

    fixed_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = (
            "exam",
            "category",
        )

    def clean(self):
        if self.fixed_count and self.percentage:
            raise ValidationError(
                "Use either percentage OR fixed count, not both."
            )

        if self.percentage > 100:
            raise ValidationError(
                "Percentage cannot exceed 100."
            )

    def __str__(self):
        return f"{self.exam} → {self.category}"