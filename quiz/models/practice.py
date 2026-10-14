from django.conf import settings
from django.db import models

from .category import Category


class PracticeStat(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="practice_stats",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    total_attempted = models.PositiveIntegerField(default=0)

    total_correct = models.PositiveIntegerField(default=0)

    last_practice_date = models.DateField(
        null=True,
        blank=True,
    )

    streak = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (
            "user",
            "category",
        )

    @property
    def accuracy(self):

        if self.total_attempted == 0:
            return 0

        return round(
            self.total_correct /
            self.total_attempted * 100,
            2,
        )

    def __str__(self):

        return (
            f"{self.user} | "
            f"{self.category} | "
            f"{self.total_correct}/{self.total_attempted}"
        )