from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from quiz.utils import SafeStrMixin


class UserExam(SafeStrMixin, models.Model):
    STATUS_STARTED = "started"
    STATUS_SUBMITTED = "submitted"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_EXPIRED, "Expired"),
    ]

    STR_FIELDS = ("user", "exam")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    exam = models.ForeignKey("Exam", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_STARTED,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    question_order = models.JSONField(default=list, help_text="Ordered list of question IDs")
    current_index = models.PositiveIntegerField(default=0)
    score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "exam"]),
            models.Index(fields=["user", "submitted_at"]),
        ]

    def save(self, *args, **kwargs):
        """Enforce one active attempt per user/exam on MySQL."""
        if self.submitted_at is None:
            with transaction.atomic():
                User.objects.select_for_update().get(pk=self.user_id)
                duplicate = type(self).objects.filter(
                    user_id=self.user_id,
                    exam_id=self.exam_id,
                    submitted_at__isnull=True,
                ).exclude(pk=self.pk).exists()
                if duplicate:
                    raise ValidationError(
                        "The user already has an active attempt for this exam."
                    )
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def time_remaining(self):
        elapsed = (timezone.now() - self.started_at).total_seconds()
        return max(0, int(self.exam.duration_seconds - elapsed))

    def is_active(self):
        return self.status == self.STATUS_STARTED and self.time_remaining() > 0

    def mark_expired(self):
        if self.status == self.STATUS_STARTED:
            self.status = self.STATUS_EXPIRED
            self.submitted_at = timezone.now()
            self.passed = False
            self.save(update_fields=["status", "submitted_at", "passed"])

    def submit(self, score, is_mock=False):
        self.score = score
        self.submitted_at = timezone.now()
        self.status = self.STATUS_SUBMITTED
        self.passed = None if is_mock else score >= self.exam.passing_score
        self.save()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            if self.submitted_at is None:
                self.submitted_at = timezone.now()
                self.save(update_fields=["submitted_at"])
            super().delete(*args, **kwargs)

    def is_expired(self):
        if self.submitted_at:
            return False
        if not self.exam.duration_seconds:
            return False
        expiry_time = self.started_at + timedelta(seconds=self.exam.duration_seconds)
        return timezone.now() > expiry_time
