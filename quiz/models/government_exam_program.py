from django.db import models

from courses.models import Course
from .content_vertical import ContentVertical
from .country import Country
from .government_body import GovernmentBody
from .government_job import GovernmentJob


class GovernmentExamProgram(models.Model):
    """Stable identity of a government recruitment/exam program."""

    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="exam_programs")
    government_body = models.ForeignKey(GovernmentBody, on_delete=models.PROTECT, related_name="exam_programs")
    content_vertical = models.ForeignKey(ContentVertical, on_delete=models.PROTECT, related_name="government_exam_programs")
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=140)
    slug = models.SlugField(max_length=300)
    description = models.TextField(blank=True)
    jobs = models.ManyToManyField(GovernmentJob, blank=True, related_name="exam_programs")
    courses = models.ManyToManyField(Course, blank=True, related_name="government_exam_programs")
    official_website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["government_body", "code"], name="uniq_program_body_code")]
        indexes = [
            models.Index(fields=["country", "is_active"], name="program_country_active_idx"),
            models.Index(fields=["government_body", "is_active"], name="program_body_active_idx"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.government_body_id and self.country_id and self.government_body.country_id != self.country_id:
            raise ValidationError({"country": "Program country must match the government body's country."})

    def __str__(self):
        return self.name
