from django.conf import settings
from django.db import models
from quiz.models import Exam, ExamTrack


class EnrollmentLead(models.Model):
    STATUS_CHOICES = (
        ("new", "New"),
        ("contacted", "Contacted"),
        ("converted", "Converted"),
        ("lost", "Lost"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_enrollment_leads",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="account_enrollment_leads",
    )
    track = models.ForeignKey(
        ExamTrack,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account_enrollment_leads",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Enrollment Lead"
        verbose_name_plural = "Enrollment Leads"

    def __str__(self):
        return f"{self.user} → {self.exam} ({self.status})"
