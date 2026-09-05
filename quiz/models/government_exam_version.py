from django.db import models

from .government_exam_program import GovernmentExamProgram


class GovernmentExamVersion(models.Model):
    """Versioned syllabus/structure for a government exam program."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"
    STATUS_CHOICES = ((DRAFT, "Draft"), (ACTIVE, "Active"), (RETIRED, "Retired"))

    program = models.ForeignKey(GovernmentExamProgram, on_delete=models.PROTECT, related_name="versions")
    version = models.CharField(max_length=80)
    slug = models.SlugField(max_length=180)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    official_syllabus_url = models.URLField(blank=True)
    official_notification_url = models.URLField(blank=True)
    source_published_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_from", "-created_at"]
        constraints = [models.UniqueConstraint(fields=["program", "version"], name="uniq_exam_program_version")]
        indexes = [
            models.Index(fields=["program", "status"], name="version_program_status_idx"),
            models.Index(fields=["status", "effective_from"], name="version_status_effective_idx"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "Effective end date cannot precede the start date."})

    def __str__(self):
        return f"{self.program.name} - {self.version}"
