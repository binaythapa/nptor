from django.db import models

from .country import Country


class GovernmentBody(models.Model):
    """Government or recruiting authority that owns an exam program."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="government_bodies")
    name = models.CharField(max_length=200)
    code = models.SlugField(max_length=100)
    slug = models.SlugField(max_length=220)
    official_website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["country", "code"], name="uniq_body_country_code")]
        indexes = [
            models.Index(fields=["country", "is_active"], name="body_country_active_idx"),
            models.Index(fields=["country", "name"], name="body_country_name_idx"),
        ]

    def __str__(self):
        return self.name
