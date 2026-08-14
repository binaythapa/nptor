from datetime import timedelta
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


from datetime import timedelta
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailOTP(models.Model):

    PURPOSE_LOGIN = "login"
    PURPOSE_PASSWORD_RESET = "password_reset"
    PURPOSE_EMAIL_VERIFICATION = "email_verification"

    PURPOSE_REGISTRATION = PURPOSE_EMAIL_VERIFICATION

    PURPOSE_CHOICES = (
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_PASSWORD_RESET, "Password Reset"),
        (PURPOSE_EMAIL_VERIFICATION, "Email Verification"),
    )

    email = models.EmailField(db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_otps",
    )

    otp_hash = models.CharField(max_length=64)

    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES,
        default=PURPOSE_LOGIN,
    )

    attempts = models.PositiveSmallIntegerField(default=0)

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
    )

    user_agent = models.TextField(
        blank=True,
        default="",
    )

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField()

    verified_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["email", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.purpose})"

    @staticmethod
    def generate_code():
        """
        Generates secure 6 digit OTP.
        """
        return f"{secrets.randbelow(900000)+100000:06}"

    @staticmethod
    def hash_code(code):
        """
        SHA256 hash.
        """
        return hashlib.sha256(
            code.encode()
        ).hexdigest()

    @classmethod
    def create_otp(
        cls,
        email,
        purpose=PURPOSE_LOGIN,
        ttl_minutes=5,
        user=None,
        ip_address=None,
        user_agent="",
    ):

        cls.objects.filter(
            email=email,
            purpose=purpose,
            is_used=False,
        ).update(
            is_used=True
        )

        code = cls.generate_code()

        otp = cls.objects.create(
            email=email,
            user=user,
            otp_hash=cls.hash_code(code),
            purpose=purpose,
            expires_at=timezone.now()
            + timedelta(minutes=ttl_minutes),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return otp, code

    def verify(self, code):

        if not self.is_valid():
            return False

        if self.otp_hash != self.hash_code(code):

            self.attempts += 1

            self.save(
                update_fields=["attempts"]
            )

            return False

        self.is_used = True

        self.verified_at = timezone.now()

        self.save(
            update_fields=[
                "is_used",
                "verified_at",
            ]
        )

        return True

    def is_valid(self):

        return (
            not self.is_used
            and self.expires_at > timezone.now()
            and self.attempts < 5
        )


from django.db import models
from django.contrib.auth.models import User


class SocialAccount(models.Model):
    """
    Stores OAuth/social login information.

    One Django User can be linked with one or more providers.
    Example:
        Google
        Microsoft
        GitHub
        Apple
    """

    PROVIDER_GOOGLE = "google"
    PROVIDER_MICROSOFT = "microsoft"
    PROVIDER_GITHUB = "github"
    PROVIDER_APPLE = "apple"

    PROVIDERS = (
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_MICROSOFT, "Microsoft"),
        (PROVIDER_GITHUB, "GitHub"),
        (PROVIDER_APPLE, "Apple"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )

    provider = models.CharField(
        max_length=30,
        choices=PROVIDERS,
    )

    # Unique ID returned by OAuth provider
    provider_id = models.CharField(
        max_length=255,
    )

    email = models.EmailField(
        db_index=True,
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
    )

    first_name = models.CharField(
        max_length=150,
        blank=True,
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
    )

    profile_picture = models.URLField(
        blank=True,
        null=True,
    )

    locale = models.CharField(
        max_length=20,
        blank=True,
    )

    email_verified = models.BooleanField(
        default=False,
    )

    raw_data = models.JSONField(
        blank=True,
        null=True,
    )

    last_login_at = models.DateTimeField(
        auto_now=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_id"],
                name="unique_social_provider",
            )
        ]

        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["email"]),
            models.Index(fields=["provider", "email"]),
        ]

    def __str__(self):
        return f"{self.user.email} ({self.provider})"