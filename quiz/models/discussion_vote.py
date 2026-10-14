from django.conf import settings
from django.db import models


class DiscussionVote(models.Model):

    UPVOTE = 1
    DOWNVOTE = -1

    VOTE_CHOICES = [
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    discussion = models.ForeignKey(
        "QuestionDiscussion",
        on_delete=models.CASCADE,
        related_name="votes",
    )

    value = models.SmallIntegerField(
        choices=VOTE_CHOICES,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        unique_together = (
            "user",
            "discussion",
        )

        indexes = [
            models.Index(
                fields=["discussion"]
            ),
            models.Index(
                fields=["value"]
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.value}"