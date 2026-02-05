from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random


class EmailOTP(models.Model):
    PURPOSE_LOGIN = "login"
    PURPOSE_PASSWORD_RESET = "password_reset"

    # ✅ canonical name
    PURPOSE_EMAIL_VERIFICATION = "email_verification"

    # ✅ alias for registration flow (IMPORTANT)
    PURPOSE_REGISTRATION = PURPOSE_EMAIL_VERIFICATION

    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
        (PURPOSE_EMAIL_VERIFICATION, "Email Verification"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_otps"
    )
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["user", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.user} ({self.purpose})"

    @staticmethod
    def create_otp(user, purpose="login", ttl_minutes=5):
        """
        Creates a single valid OTP per user & purpose.
        Invalidates any previous unused OTPs.
        """
        EmailOTP.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False
        ).update(is_used=True)

        return EmailOTP.objects.create(
            user=user,
            purpose=purpose,
            code=str(random.randint(100000, 999999)),
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

    def is_valid(self):
        """Check if OTP is usable"""
        return not self.is_used and self.expires_at > timezone.now()
