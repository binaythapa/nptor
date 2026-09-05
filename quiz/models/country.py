from django.db import models


class Country(models.Model):
    """Country used to scope government-exam catalog data."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=3, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="country_active_name_idx"),
        ]

    def __str__(self):
        return self.name
