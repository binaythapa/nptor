from django.db import models

from .country import Country
from .government_body import GovernmentBody


class GovernmentJob(models.Model):
    """A government post, job, cadre, or recruitment target."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="government_jobs")
    government_body = models.ForeignKey(GovernmentBody, on_delete=models.PROTECT, related_name="government_jobs")
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=120)
    slug = models.SlugField(max_length=280)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["government_body", "code"], name="uniq_job_body_code")]
        indexes = [
            models.Index(fields=["government_body", "is_active"], name="job_body_active_idx"),
            models.Index(fields=["country", "is_active"], name="job_country_active_idx"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.government_body_id and self.country_id and self.government_body.country_id != self.country_id:
            raise ValidationError({"country": "Job country must match the government body's country."})

    def __str__(self):
        return self.name
