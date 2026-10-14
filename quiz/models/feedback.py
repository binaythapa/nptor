from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class QuestionFeedback(models.Model):

    STATUS_NEW = "new"
    STATUS_REVIEWED = "reviewed"
    STATUS_RESOLVED = "resolved"

    STATUS_CHOICES = (
        (STATUS_NEW, "New"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_RESOLVED, "Resolved"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="question_feedbacks",
    )

    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )

    user_exam = models.ForeignKey(
        "UserExam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_feedbacks",
    )

    comment = models.TextField(
        blank=True,
    )

    is_answer_incorrect = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )

    staff_note = models.TextField(
        blank=True,
    )

    def __str__(self):

        label = (
            "Incorrect-answer report"
            if self.is_answer_incorrect
            else "Comment"
        )

        return (
            f"{label} by "
            f"{self.user} "
            f"on Q#{self.question_id}"
        )