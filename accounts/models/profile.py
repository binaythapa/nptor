from django.db import models
from django.conf import settings

from phone_field import PhoneField
from django_countries.fields import CountryField


class UserProfile(models.Model):
    """Extended profile information for a Django user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    country = CountryField(blank=True, null=True)
    phone = PhoneField(blank=True, null=True, help_text="Contact phone number")
    phone_verified = models.BooleanField(default=False, help_text="Has the user verified their mobile number via OTP?")
    email_verified = models.BooleanField(default=False, help_text="Has the user verified their email address?")
    address = models.CharField(max_length=200, blank=True, null=True)
    accepted_policy = models.BooleanField(default=False, help_text="User accepted the Terms & Privacy Policy")
    is_platform_admin = models.BooleanField(default=False, db_index=True, help_text="Explicit NPTOR platform administrator permission.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()
