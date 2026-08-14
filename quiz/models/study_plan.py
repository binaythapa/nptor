import math
import statistics
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class StudyPlan(models.Model):

    MAX_EXTENSION_DAYS = 3

    # =====================================================
    # PREDEFINED PLAN TYPES
    # =====================================================

    PLAN_7 = 7
    PLAN_15 = 15
    PLAN_30 = 30

    PLAN_CHOICES = [
        (PLAN_7, "7-Day Crash Plan"),
        (PLAN_15, "15-Day Balanced Plan"),
        (PLAN_30, "30-Day Mastery Plan"),
    ]

    # =====================================================
    # CORE RELATIONS
    # =====================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_plans",
    )

    domain = models.ForeignKey(
        "Domain",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional domain focus",
    )

    # =====================================================
    # PLAN CONFIGURATION
    # =====================================================

    plan_type = models.PositiveIntegerField(
        choices=PLAN_CHOICES,
    )

    total_days = models.PositiveIntegerField()

    questions_per_day = models.PositiveIntegerField()

    question_ids = models.JSONField(
        default=list,
        help_text="Ordered question IDs for entire plan",
    )

    daily_progress = models.JSONField(
        default=dict,
        help_text="Map day_index -> completed_count",
    )

    # =====================================================
    # TIMING
    # =====================================================

    start_date = models.DateField(
        default=timezone.now,
    )

    extension_days = models.PositiveIntegerField(
        default=0,
        help_text="Auto-extended days due to missed schedule",
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True,
    )

    is_completed = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    # =====================================================
    # ANALYTICS
    # =====================================================

    total_attempted = models.PositiveIntegerField(
        default=0,
    )

    total_correct = models.PositiveIntegerField(
        default=0,
    )

    category_stats = models.JSONField(
        default=dict,
        blank=True,
    )

    # =====================================================
    # DAILY STREAK
    # =====================================================

    current_streak = models.PositiveIntegerField(
        default=0,
    )

    longest_streak = models.PositiveIntegerField(
        default=0,
    )

    last_activity_date = models.DateField(
        null=True,
        blank=True,
    )

    # =====================================================
    # DIFFICULTY ANALYTICS
    # =====================================================

    difficulty_stats = models.JSONField(
        default=dict,
        blank=True,
    )

    # =====================================================
    # XP SYSTEM
    # =====================================================

    xp = models.PositiveIntegerField(
        default=0,
    )

    level = models.PositiveIntegerField(
        default=1,
    )

    performance_history = models.JSONField(
        default=list,
        blank=True,
    )

    exam_mode = models.BooleanField(
        default=False,
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "is_active"]
            ),
            models.Index(
                fields=["user", "is_completed"]
            ),
        ]

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):
        if self.total_days <= 0:
            raise ValidationError(
                "Total days must be greater than 0."
            )

        if self.questions_per_day <= 0:
            raise ValidationError(
                "Questions per day must be greater than 0."
            )

        if not isinstance(self.question_ids, list):
            raise ValidationError(
                "question_ids must be a list."
            )

    # =====================================================
    # PLAN CALCULATIONS
    # =====================================================

    def total_questions(self):
        return (
            self.total_days *
            self.questions_per_day
        )

    def total_plan_days(self):
        """
        Includes extension days.
        """
        return (
            self.total_days +
            self.extension_days
        )

    def get_day_index(self):
        today = timezone.now().date()

        return (
            today -
            self.start_date
        ).days

    def get_today_question_ids(self):
        day_index = self.get_day_index()

        start = (
            day_index *
            self.questions_per_day
        )

        end = (
            start +
            self.questions_per_day
        )

        return self.question_ids[start:end]

    def get_today_completed_count(self):
        day_index = str(
            self.get_day_index()
        )

        return self.daily_progress.get(
            day_index,
            0,
        )

    def increment_today_progress(self):
        day_index = str(
            self.get_day_index()
        )

        current = self.daily_progress.get(
            day_index,
            0,
        )

        self.daily_progress[day_index] = (
            current + 1
        )

        self.save(
            update_fields=["daily_progress"]
        )

    def completion_percentage(self):
        total_done = sum(
            self.daily_progress.values()
        )

        total_questions = self.total_questions()

        if total_questions == 0:
            return 0

        return round(
            (
                total_done /
                total_questions
            ) * 100,
            2,
        )

    def mark_completed_if_finished(self):
        if (
            sum(self.daily_progress.values())
            >= self.total_questions()
        ):
            self.is_completed = True
            self.is_active = False

            self.save(
                update_fields=[
                    "is_completed",
                    "is_active",
                ]
            )

            return True

        return False

    # =====================================================
    # EXTENSION
    # =====================================================

    def auto_extend_if_needed(self):
        """
        Extend plan if user has crossed planned duration.
        Capped by MAX_EXTENSION_DAYS.
        """

        today_index = self.get_day_index()

        allowed_days = (
            self.total_days +
            self.extension_days
        )

        if today_index >= allowed_days:

            extra_needed = (
                today_index -
                allowed_days +
                1
            )

            remaining_capacity = (
                self.MAX_EXTENSION_DAYS -
                self.extension_days
            )

            if remaining_capacity <= 0:
                return

            extend_by = min(
                extra_needed,
                remaining_capacity,
            )

            self.extension_days += extend_by

            self.save(
                update_fields=["extension_days"]
            )

    # =====================================================
    # ACCURACY
    # =====================================================

    def accuracy_percentage(self):
        if self.total_attempted == 0:
            return 0

        return round(
            (
                self.total_correct /
                self.total_attempted
            ) * 100,
            2,
        )

    # =====================================================
    # CATEGORY ANALYTICS
    # =====================================================

    def get_category_accuracy(self, category_id):
        stats = self.category_stats or {}

        data = stats.get(
            str(category_id)
        )

        if not data or data["attempted"] == 0:
            return 0

        return round(
            (
                data["correct"] /
                data["attempted"]
            ) * 100,
            2,
        )

    # =====================================================
    # DIFFICULTY MASTERy
    # =====================================================

    def difficulty_weighted_mastery(self):
        """
        Weighted mastery:

        easy   = 1x
        medium = 1.5x
        hard   = 2x
        """

        stats = self.difficulty_stats or {}

        weights = {
            "easy": 1,
            "medium": 1.5,
            "hard": 2,
        }

        weighted_score = 0
        weighted_total = 0

        for difficulty, data in stats.items():

            attempted = data.get(
                "attempted",
                0,
            )

            correct = data.get(
                "correct",
                0,
            )

            if attempted == 0:
                continue

            accuracy = (
                correct /
                attempted
            )

            weight = weights.get(
                difficulty,
                1,
            )

            weighted_score += (
                accuracy *
                weight
            )

            weighted_total += weight

        if weighted_total == 0:
            return 0

        return round(
            (
                weighted_score /
                weighted_total
            ) * 100,
            2,
        )

    # =====================================================
    # CERTIFICATION READINESS
    # =====================================================

    def certification_readiness(self):
        """
        Combines:

        - Accuracy
        - Difficulty mastery
        - Completion %
        """

        base_accuracy = (
            self.accuracy_percentage()
        )

        difficulty_score = (
            self.difficulty_weighted_mastery()
        )

        completion = (
            self.completion_percentage()
        )

        readiness = (
            (base_accuracy * 0.5) +
            (difficulty_score * 0.3) +
            (completion * 0.2)
        )

        return round(
            min(readiness, 100),
            2,
        )

    def recommend_next_plan_type(self):
        readiness = (
            self.certification_readiness()
        )

        if readiness >= 85:
            return self.PLAN_30

        elif readiness >= 65:
            return self.PLAN_15

        return self.PLAN_7

    def certification_badge(self):
        """
        Badge based on mastery score.
        """

        mastery = self.accuracy_percentage()

        if mastery >= 90:
            return "Platinum"

        elif mastery >= 80:
            return "Gold"

        elif mastery >= 70:
            return "Silver"

        elif mastery >= 60:
            return "Bronze"

        return None

    # =====================================================
    # XP
    # =====================================================

    def add_xp(self, amount):
        self.xp += amount
        self.level = self.calculate_level()

        self.save(
            update_fields=[
                "xp",
                "level",
            ]
        )

    def calculate_level(self):
        return int(
            math.sqrt(
                self.xp / 50
            )
        ) + 1

    # =====================================================
    # XP LEVEL PROGRESSION
    # =====================================================

    def apply_xp(self, xp_earned):
        """
        Adds XP and auto-levels user if threshold crossed.
        Supports multiple level jumps.
        """

        self.xp += xp_earned

        leveled_up = False

        while (
            self.xp >=
            self.xp_required_for_next_level()
        ):
            self.xp -= (
                self.xp_required_for_next_level()
            )

            self.level += 1

            leveled_up = True

        return leveled_up

    def xp_required_for_next_level(self):
        """
        Progressive XP curve:

        Level 1 -> 100
        Level 2 -> 150
        Level 3 -> 225
        Level 4 -> 340
        """

        return int(
            100 *
            (
                1.5 **
                (self.level - 1)
            )
        )

    def level_progress_percent(self):
        """
        Returns progress toward next level.
        """

        if not hasattr(self, "xp"):
            return 0

        required = (
            self.xp_required_for_next_level()
        )

        if required == 0:
            return 0

        progress = (
            self.xp %
            required
        ) / required

        return round(
            progress * 100,
            2,
        )

    # =====================================================
    # STREAK
    # =====================================================

    def update_streak(self):
        today = timezone.now().date()

        if self.last_activity_date == today:
            return

        if (
            self.last_activity_date ==
            today - timedelta(days=1)
        ):
            self.current_streak += 1

        else:
            self.current_streak = 1

        self.last_activity_date = today

        if (
            self.current_streak >
            self.longest_streak
        ):
            self.longest_streak = (
                self.current_streak
            )

        self.save(
            update_fields=[
                "current_streak",
                "longest_streak",
                "last_activity_date",
            ]
        )

    # =====================================================
    # CERTIFICATION PREDICTION
    # =====================================================

    def certification_prediction(self):
        """
        Returns:

        - predicted_score
        - pass_probability
        - confidence
        """

        total_attempted = (
            self.total_attempted
        )

        total_correct = (
            self.total_correct
        )

        if total_attempted == 0:
            return {
                "predicted_score": 0,
                "pass_probability": 0,
                "confidence": 0,
            }

        # Bayesian adjusted accuracy

        adjusted_accuracy = (
            (
                total_correct + 20
            ) /
            (
                total_attempted + 40
            )
        ) * 100

        # Difficulty weighted mastery

        weighted_mastery = (
            self.difficulty_weighted_mastery()
        )

        # Consistency score

        days_practiced = len(
            [
                value
                for value in (
                    self.daily_progress or {}
                ).values()
                if value > 0
            ]
        )

        total_days = (
            self.total_plan_days()
        )

        consistency_score = (
            (
                days_practiced /
                total_days
            ) * 100
            if total_days > 0
            else 0
        )

        # Predicted score

        predicted_score = (
            adjusted_accuracy * 0.6
            +
            weighted_mastery * 0.3
            +
            consistency_score * 0.1
        )

        predicted_score = round(
            max(
                min(
                    predicted_score,
                    100,
                ),
                0,
            ),
            2,
        )

        # Pass probability

        pass_probability = (
            1 /
            (
                1 +
                math.exp(
                    -(
                        predicted_score - 70
                    ) / 5
                )
            )
        )

        pass_probability = round(
            pass_probability * 100,
            2,
        )

        # Confidence

        confidence = min(
            100,
            round(
                (
                    total_attempted /
                    300
                ) * 100,
                2,
            ),
        )

        return {
            "predicted_score": predicted_score,
            "pass_probability": pass_probability,
            "confidence": confidence,
        }

    # =====================================================
    # PERFORMANCE VOLATILITY
    # =====================================================

    def score_volatility(self):
        """
        Measures stability of recent performance.
        Lower = more stable.
        """

        history = (
            self.performance_history or []
        )

        if len(history) < 5:
            return 0

        return round(
            statistics.pstdev(history),
            2,
        )

    # =====================================================
    # GLOBAL COMPETITIVE SCORE
    # =====================================================

    def global_competitive_score(self):
        """
        Global ranking score across all active users.
        Weighted competitive index.
        """

        readiness = (
            self.certification_readiness()
        )

        mastery = (
            self.difficulty_weighted_mastery()
        )

        streak = min(
            self.current_streak,
            30,
        )

        stability = (
            1 -
            self.score_volatility()
        )

        xp_component = (
            min(
                self.xp / 1000,
                1,
            ) * 100
        )

        score = (
            readiness * 0.35
            +
            mastery * 0.25
            +
            xp_component * 0.15
            +
            streak * 0.10
            +
            stability * 100 * 0.15
        )

        return round(
            score,
            2,
        )

    # =====================================================
    # COMPETITIVE TIER
    # =====================================================

    def competitive_tier(self, percentile):

        if percentile >= 95:
            return "Grandmaster"

        elif percentile >= 85:
            return "Platinum"

        elif percentile >= 70:
            return "Gold"

        elif percentile >= 40:
            return "Silver"

        return "Bronze"

    # =====================================================
    # DAILY ANALYTICS SNAPSHOT
    # =====================================================

    def save_daily_snapshot(self):
        from .study_plan_analytics import (
            StudyPlanAnalyticsSnapshot
        )

        today = timezone.now().date()

        if self.snapshots.filter(
            date=today
        ).exists():
            return

        prediction = (
            self.certification_prediction()
        )

        StudyPlanAnalyticsSnapshot.objects.create(
            plan=self,
            accuracy=self.accuracy_percentage(),
            readiness=self.certification_readiness(),
            mastery=self.mastery_index(),
            predicted_score=prediction[
                "predicted_score"
            ],
            pass_probability=prediction[
                "pass_probability"
            ],
            volatility=self.score_volatility(),
            xp=self.xp,
            level=self.level,
        )

    # =====================================================
    # MASTERY INDEX
    # =====================================================

    def mastery_index(self):
        """
        Weighted mastery metric used for
        analytics and snapshots.
        """

        if self.total_attempted == 0:
            return 0

        accuracy = (
            self.total_correct /
            self.total_attempted
        ) * 100

        volume_score = min(
            100,
            (
                self.total_attempted /
                200
            ) * 100,
        )

        days_practiced = len(
            [
                value
                for value in (
                    self.daily_progress or {}
                ).values()
                if value > 0
            ]
        )

        total_days = (
            self.total_plan_days()
            if hasattr(
                self,
                "total_plan_days"
            )
            else 1
        )

        consistency_ratio = (
            days_practiced /
            total_days
            if total_days > 0
            else 0
        )

        consistency_score = (
            consistency_ratio * 100
        )

        mastery = (
            (accuracy * 0.6)
            +
            (volume_score * 0.25)
            +
            (consistency_score * 0.15)
        )

        return round(
            max(mastery, 0),
            2,
        )

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return (
            f"{self.user} | "
            f"{self.get_plan_type_display()}"
        )