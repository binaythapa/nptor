from django.db import models


class ContactMethod(models.Model):
    """
    Lookup table for contact methods.
    """

    code = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(
        max_length=50,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name