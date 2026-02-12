from django.db import models
from django.conf import settings
from phone_field import PhoneField
from django_countries.fields import CountryField


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # 🌍 Optional Country
    country = CountryField(blank=True, null=True)

    # 📱 Optional Mobile (Future OTP Ready)
    phone = PhoneField(
        blank=True,
        null=True,
        help_text="Contact phone number",
    )

    # 🔐 Future OTP Support
    phone_verified = models.BooleanField(
        default=False,
        help_text="Has user verified mobile number via OTP?"
    )

    # 📍 Optional Address
    address = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    # 📜 Required During Registration
    accepted_policy = models.BooleanField(
        default=False,
        help_text="User accepted terms & privacy policy",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()
