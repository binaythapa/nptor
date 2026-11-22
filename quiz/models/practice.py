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


class UserPracticeStreak(models.Model):
    """
    Centralized practice streak tracker for authenticated students.
    Maintains current and longest daily practice streaks across all practice activities.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="practice_streak",
    )

    current_streak = models.PositiveIntegerField(default=0)

    longest_streak = models.PositiveIntegerField(default=0)

    last_activity_date = models.DateField(null=True, blank=True)

    total_active_days = models.PositiveIntegerField(default=0)

    total_questions_practiced = models.PositiveIntegerField(default=0)

    total_questions_correct = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "current_streak"], name="user_practice_streak_idx"),
            models.Index(fields=["last_activity_date"], name="user_practice_date_idx"),
        ]

    def get_effective_current_streak(self, today=None):
        """
        Returns active streak based on business date.
        If last activity was today or yesterday, streak is intact.
        If missed yesterday or earlier, effective streak is 0.
        """
        if not self.last_activity_date or self.current_streak == 0:
            return 0
        if today is None:
            from quiz.services.streak_service import get_business_today
            today = get_business_today()
        diff = (today - self.last_activity_date).days
        if diff <= 1:
            return self.current_streak
        return 0

    def __str__(self):
        return f"{self.user} | Current Streak: {self.current_streak} (Best: {self.longest_streak})"


class DailyPracticeLog(models.Model):
    """
    Log of daily qualifying practice activity.
    Guarantees at most 1 qualifying entry per user per calendar day via unique constraint.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_practice_logs",
    )

    activity_date = models.DateField(db_index=True)

    questions_practiced = models.PositiveIntegerField(default=0)

    questions_correct = models.PositiveIntegerField(default=0)

    is_qualifying = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "activity_date"],
                name="uniq_user_daily_practice_log",
            )
        ]
        indexes = [
            models.Index(fields=["user", "activity_date"], name="user_daily_log_idx"),
        ]
        ordering = ["-activity_date"]

    def __str__(self):
        return f"{self.user} | {self.activity_date} | {self.questions_practiced} Qs"
