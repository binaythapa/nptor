from django.db import models
from django.conf import settings

from phone_field import PhoneField
from django_countries.fields import CountryField


class UserProfile(models.Model):
    """
    Extended profile information for a Django user.

    Authentication credentials remain on the User model.
    UserProfile stores additional account information such as
    country, phone number, address, and verification status.
    """

    # ============================================================
    # USER
    # ============================================================

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # ============================================================
    # LOCATION
    # ============================================================

    country = CountryField(
        blank=True,
        null=True,
    )

    # ============================================================
    # PHONE
    # ============================================================

    phone = PhoneField(
        blank=True,
        null=True,
        help_text="Contact phone number",
    )

    phone_verified = models.BooleanField(
        default=False,
        help_text="Has the user verified their mobile number via OTP?",
    )

    # ============================================================
    # EMAIL VERIFICATION
    # ============================================================

    email_verified = models.BooleanField(
        default=False,
        help_text="Has the user verified their email address?",
    )

    # ============================================================
    # ADDRESS
    # ============================================================

    address = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    # ============================================================
    # REGISTRATION / POLICY
    # ============================================================

    accepted_policy = models.BooleanField(
        default=False,
        help_text="User accepted the Terms & Privacy Policy",
    )

    # ============================================================
    # TIMESTAMPS
    # ============================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ============================================================
    # STRING REPRESENTATION
    # ============================================================

    def __str__(self):
        return self.user.get_username()