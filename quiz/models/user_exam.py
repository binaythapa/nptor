from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from quiz.utils import SafeStrMixin


class UserExam(SafeStrMixin, models.Model):

    # =====================================================
    # STATUS
    # =====================================================

    STATUS_STARTED = "started"
    STATUS_SUBMITTED = "submitted"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_EXPIRED, "Expired"),
    ]

    # =====================================================
    # SAFE STRING REPRESENTATION
    # =====================================================

    STR_FIELDS = (
        "user",
        "exam",
    )

    # =====================================================
    # USER
    # =====================================================

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )

    # =====================================================
    # EXAM
    # =====================================================

    exam = models.ForeignKey(
        "Exam",
        on_delete=models.CASCADE,
    )

    # =====================================================
    # STATUS
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_STARTED,
        db_index=True,
    )

    # =====================================================
    # TIMING
    # =====================================================

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =====================================================
    # QUESTION NAVIGATION
    # =====================================================

    question_order = models.JSONField(
        default=list,
        help_text="Ordered list of question IDs",
    )

    current_index = models.PositiveIntegerField(
        default=0,
    )

    # =====================================================
    # RESULT
    # =====================================================

    score = models.FloatField(
        null=True,
        blank=True,
    )

    passed = models.BooleanField(
        null=True,
        blank=True,
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "user",
                    "exam",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "submitted_at",
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "exam",
                ],
                condition=Q(
                    submitted_at__isnull=True
                ),
                name="one_active_attempt_per_exam",
            ),
        ]

    # =====================================================
    # TIMER
    # =====================================================

    def time_remaining(self):
        """
        Return remaining exam time in seconds.

        Returns 0 when the exam time has elapsed.
        """

        elapsed = (
            timezone.now() - self.started_at
        ).total_seconds()

        return max(
            0,
            int(
                self.exam.duration_seconds
                - elapsed
            ),
        )

    # =====================================================
    # ACTIVE STATUS
    # =====================================================

    def is_active(self):
        """
        Return True when the attempt is started
        and there is still time remaining.
        """

        return (
            self.status == self.STATUS_STARTED
            and self.time_remaining() > 0
        )

    # =====================================================
    # EXPIRE
    # =====================================================

    def mark_expired(self):
        """
        Mark an active attempt as expired.
        """

        if self.status == self.STATUS_STARTED:

            self.status = self.STATUS_EXPIRED

            self.submitted_at = timezone.now()

            self.passed = False

            self.save(
                update_fields=[
                    "status",
                    "submitted_at",
                    "passed",
                ]
            )

    # =====================================================
    # SUBMIT
    # =====================================================

    def submit(self, score, is_mock=False):
        """
        Submit the exam.

        For mock exams:
            passed = None

        For normal exams:
            passed is determined using the exam's
            configured passing score.
        """

        self.score = score

        self.submitted_at = timezone.now()

        self.status = self.STATUS_SUBMITTED

        self.passed = (
            None
            if is_mock
            else score >= self.exam.passing_score
        )

        self.save()

    # =====================================================
    # DELETE
    # =====================================================

    def delete(self, *args, **kwargs):
        """
        Delete the attempt safely.

        The database constraint
        'one_active_attempt_per_exam'
        applies while submitted_at is NULL.

        Therefore, if an active attempt is being deleted,
        mark submitted_at first and then delete it.
        """

        with transaction.atomic():

            if self.submitted_at is None:

                self.submitted_at = timezone.now()

                self.save(
                    update_fields=[
                        "submitted_at",
                    ]
                )

            super().delete(
                *args,
                **kwargs
            )

    # =====================================================
    # EXPIRY CHECK
    # =====================================================

    def is_expired(self):
        """
        Determine whether the exam attempt has expired.
        """

        if self.submitted_at:
            return False

        if not self.exam.duration_seconds:
            return False

        expiry_time = (
            self.started_at
            + timedelta(
                seconds=self.exam.duration_seconds
            )
        )

        return timezone.now() > expiry_time