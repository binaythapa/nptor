from django.contrib.auth.models import User
from django.db import models


class LeaderboardEntry(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
    )

    score = models.FloatField(
        default=0,
    )

    rank = models.PositiveIntegerField(
        default=0,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user} - Rank {self.rank}"