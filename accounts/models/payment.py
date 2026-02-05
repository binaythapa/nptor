from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

User = settings.AUTH_USER_MODEL


class Payment(models.Model):
    """
    Immutable payment record.
    One row = one completed payment.
    """

    # ===============================
    # PAYMENT METHODS
    # ===============================
    METHOD_UPI = "upi"
    METHOD_CARD = "card"
    METHOD_NETBANKING = "netbanking"
    METHOD_WALLET = "wallet"
    METHOD_CASH = "cash"
    METHOD_OTHER = "other"

    PAYMENT_METHOD_CHOICES = [
        (METHOD_UPI, "UPI"),
        (METHOD_CARD, "Card"),
        (METHOD_NETBANKING, "Net Banking"),
        (METHOD_WALLET, "Wallet"),
        (METHOD_CASH, "Cash / Manual"),
        (METHOD_OTHER, "Other"),
    ]

    # ===============================
    # CORE RELATIONSHIPS
    # ===============================
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments"
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments"
    )

    # ===============================
    # PAYMENT DATA
    # ===============================
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="INR"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Gateway transaction / reference ID"
    )

    remarks = models.TextField(
        blank=True,
        help_text="Admin notes or gateway response"
    )

    paid_at = models.DateTimeField(
        auto_now_add=True
    )

    created_by_admin = models.BooleanField(
        default=False,
        help_text="True if payment was recorded manually by admin"
    )

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-paid_at"]
        indexes = [
            models.Index(fields=["paid_at"]),
            models.Index(fields=["payment_method"]),
            models.Index(fields=["user"]),
        ]

    # ===============================
    # VALIDATION
    # ===============================
    def clean(self):
        """
        Enforce business rules.
        """
        if self.track and self.exam:
            raise ValidationError(
                "Payment cannot be linked to both track and exam."
            )

        if not self.track and not self.exam:
            raise ValidationError(
                "Payment must be linked to either a track or an exam."
            )

        if self.amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

    # ===============================
    # HELPERS
    # ===============================
    def target_name(self):
        if self.track:
            return self.track.title
        if self.exam:
            return self.exam.title
        return "—"

    def __str__(self):
        return f"{self.user} → {self.amount} {self.currency}"
