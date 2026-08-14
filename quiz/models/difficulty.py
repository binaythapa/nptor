from django.db import models


class Difficulty(models.Model):

    name = models.CharField(
        max_length=50,
    )

    slug = models.SlugField(
        unique=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name