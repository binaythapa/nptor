from django.db import models


class UserAnswer(models.Model):

    user_exam = models.ForeignKey(
        "UserExam",
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
    )

    time_spent = models.PositiveIntegerField(
        default=0,
        help_text="Time spent on this question in seconds",
    )

    choice = models.ForeignKey(
        "Choice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    selections = models.JSONField(
        null=True,
        blank=True,
    )

    raw_answer = models.TextField(
        null=True,
        blank=True,
    )

    is_correct = models.BooleanField(
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = (
            "user_exam",
            "question",
        )

        indexes = [
            models.Index(
                fields=[
                    "user_exam",
                    "question",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"UE:{self.user_exam_id} "
            f"Q:{self.question_id}"
        )