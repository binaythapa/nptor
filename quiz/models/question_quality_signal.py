from django.conf import settings
from django.db import models


class QuestionQualitySignal(models.Model):

    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        related_name="quality_signals",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    is_confusing = models.BooleanField(
        default=False,
    )

    explanation_helpful = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = (
            "question",
            "user",
        )