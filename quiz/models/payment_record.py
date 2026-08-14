from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PaymentRecord(models.Model):
    """
    Immutable payment history.
    One row = one payment.
    """

    PAYMENT_UPI = "upi"
    PAYMENT_BANK = "bank"
    PAYMENT_CASH = "cash"
    PAYMENT_OTHER = "other"

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_UPI, "UPI"),
        (PAYMENT_BANK, "Bank Transfer"),
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_OTHER, "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_records",
    )

    track = models.ForeignKey(
        "ExamTrack",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    exam = models.ForeignKey(
        "Exam",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    paid_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by_admin = models.BooleanField(
        default=True,
    )

    def clean(self):
        if self.track and self.exam:
            raise ValidationError(
                "Payment cannot be for both track and exam."
            )

        if not self.track and not self.exam:
            raise ValidationError(
                "Payment must be linked to a track or exam."
            )

    def target_name(self):
        if self.track:
            return self.track.title

        if self.exam:
            return self.exam.title

        return "—"

    def __str__(self):
        if self.track:
            return f"{self.user} → {self.track.title}"

        if self.exam:
            return f"{self.user} → {self.exam.title}"

        return f"{self.user} → Payment"