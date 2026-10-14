from django.contrib.auth.models import User
from django.db import models


class ExamUnlockLog(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
    )

    unlocked_at = models.DateTimeField(
        auto_now_add=True,
    )

    source = models.CharField(
        max_length=30,
        default="exam_pass",
    )

    class Meta:
        unique_together = (
            "user",
            "exam",
        )

    def __str__(self):
        return f"{self.user} unlocked {self.exam}"