from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EnrollmentLead(models.Model):
    """
    User showed intent to enroll in a paid Exam or Track.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollment_leads",
    )

    track = models.ForeignKey(
        "ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollment_leads",
    )

    exam = models.ForeignKey(
        "Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="enrollment_leads",
    )

    contact_method = models.ForeignKey(
        "ContactMethod",
        on_delete=models.PROTECT,
    )

    is_converted = models.BooleanField(
        default=False,
        help_text="Set true once subscription is granted",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """
        Business rule enforcement (Python-level, safe everywhere).
        """

        if self.track and self.exam:
            raise ValidationError(
                "EnrollmentLead cannot have both track and exam."
            )

        if not self.track and not self.exam:
            raise ValidationError(
                "EnrollmentLead must have either track or exam."
            )

    def target_name(self):
        return (
            self.track.title
            if self.track
            else self.exam.title
        )

    def __str__(self):
        return (
            f"{self.user} → "
            f"{self.target_name()} "
            f"({self.contact_method})"
        )