from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    code = models.CharField(
        max_length=30,
        unique=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    # =====================================================
    # DISCOUNT
    # =====================================================

    percent_off = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Percentage discount (0–100)",
    )

    flat_off = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Flat discount amount",
    )

    # =====================================================
    # APPLICABILITY
    # =====================================================

    track = models.ForeignKey(
        "ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If set, coupon applies only to this track",
    )

    exam = models.ForeignKey(
        "Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="If set, coupon applies only to this exam",
    )

    # =====================================================
    # VALIDITY
    # =====================================================

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum times this coupon can be used",
    )

    used_count = models.PositiveIntegerField(
        default=0,
    )

    # =====================================================
    # TRIAL SUPPORT
    # =====================================================

    extra_trial_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Adds extra trial days when coupon is applied",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):
        if not self.percent_off and not self.flat_off:
            raise ValidationError(
                "Either percent_off or flat_off must be set."
            )

        if self.percent_off and self.percent_off > 100:
            raise ValidationError(
                "percent_off cannot exceed 100."
            )

        if self.track and self.exam:
            raise ValidationError(
                "Coupon cannot be linked to both track and exam."
            )

    # =====================================================
    # CORE LOGIC
    # =====================================================

    def is_valid(self):
        now = timezone.now()

        if not self.is_active:
            return False

        if self.valid_from > now or self.valid_to < now:
            return False

        if self.usage_limit and self.used_count >= self.usage_limit:
            return False

        return True

    def mark_used(self):
        self.used_count += 1

        self.save(
            update_fields=["used_count"]
        )

    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.code