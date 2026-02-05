from django.db import models
from django.conf import settings
from phone_field import PhoneField

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    phone = PhoneField(blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)

    accepted_policy = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()
