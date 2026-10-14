from django.conf import settings
from django.db import models


class QuestionDiscussion(models.Model):

    # =====================================================
    # DISCUSSION TYPES
    # =====================================================

    TYPE_COMMENT = "comment"
    TYPE_DOUBT = "doubt"
    TYPE_CORRECTION = "correction"
    TYPE_EXPLANATION = "explanation"

    DISCUSSION_TYPE_CHOICES = [
        (TYPE_COMMENT, "Comment"),
        (TYPE_DOUBT, "Doubt"),
        (TYPE_CORRECTION, "Correction"),
        (TYPE_EXPLANATION, "User Explanation"),
    ]

    # =====================================================
    # USER
    # =====================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_discussions",
    )

    # =====================================================
    # QUESTION
    # =====================================================

    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        related_name="discussions",
    )

    # =====================================================
    # EXAM ATTEMPT
    # =====================================================

    user_exam = models.ForeignKey(
        "UserExam",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discussions",
    )

    # =====================================================
    # THREAD / REPLIES
    # =====================================================

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    # =====================================================
    # TYPE & CONTENT
    # =====================================================

    discussion_type = models.CharField(
        max_length=20,
        choices=DISCUSSION_TYPE_CHOICES,
        default=TYPE_COMMENT,
    )

    content = models.TextField()

    # =====================================================
    # MODERATION / ANSWER FEEDBACK
    # =====================================================

    is_answer_incorrect = models.BooleanField(
        default=False,
    )

    is_staff_verified = models.BooleanField(
        default=False,
    )

    is_pinned = models.BooleanField(
        default=False,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =====================================================
    # RESOLUTION
    # =====================================================

    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether staff has resolved this feedback",
    )

    # =====================================================
    # SEVERITY
    # =====================================================

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default="medium",
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:
        indexes = [
            models.Index(
                fields=["question"]
            ),
            models.Index(
                fields=["discussion_type"]
            ),
            models.Index(
                fields=["is_pinned"]
            ),
            models.Index(
                fields=["created_at"]
            ),
        ]

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return (
            f"{self.discussion_type} "
            f"by {self.user} "
            f"on Q{self.question_id}"
        )