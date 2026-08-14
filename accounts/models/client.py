from django.db import models
from django.contrib.auth.models import User
from phone_field import PhoneField


class Client(models.Model):
    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    contact = PhoneField(
        blank=True,
        help_text="Contact phone number",
        null=True,
    )

    address = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    acceptpolicy = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return str(self.user)

    def fullname(self):
        return (
            self.user.first_name
            + " "
            + self.user.last_name
        )