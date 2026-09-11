from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PaymentRecord(models.Model):
    """Immutable payment history. One row = one payment."""

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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_records")
    track = models.ForeignKey("ExamTrack", null=True, blank=True, on_delete=models.SET_NULL)
    exam = models.ForeignKey("Exam", null=True, blank=True, on_delete=models.SET_NULL)
    course = models.ForeignKey("courses.Course", null=True, blank=True, on_delete=models.SET_NULL, related_name="payment_records")
    subscription_plan = models.ForeignKey("subscriptions.SubscriptionPlan", null=True, blank=True, on_delete=models.SET_NULL, related_name="payment_records")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_id = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    created_by_admin = models.BooleanField(default=True)

    def clean(self):
        if self.exam:
            if self.track or self.course or self.subscription_plan:
                raise ValidationError("Legacy exam payments cannot also target a course, track, or subscription plan.")
            return

        if self.course and self.track:
            raise ValidationError("Payment cannot be for both a course and track.")
        if self.track or self.course:
            if self.subscription_plan and self.subscription_plan.scope != "resource":
                raise ValidationError("Course/track payments require a resource subscription plan.")
            return
        if not self.subscription_plan:
            raise ValidationError("Payment must be linked to a track, course, or all-access subscription plan.")
        if not self.subscription_plan.is_all_access():
            raise ValidationError("A standalone subscription payment must use an all-access plan.")

    def target_name(self):
        if self.course:
            return self.course.title
        if self.track:
            return self.track.title
        if self.subscription_plan:
            return self.subscription_plan.name
        if self.exam:
            return self.exam.title
        return "—"

    def __str__(self):
        return f"{self.user} → {self.target_name()}"
