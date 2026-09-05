from django.db import models

from .exam import Exam
from .government_exam_version import GovernmentExamVersion


class GovernmentExamStage(models.Model):
    """A stage, paper, or assessment within a specific exam version."""

    version = models.ForeignKey(GovernmentExamVersion, on_delete=models.PROTECT, related_name="stages")
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="government_stages")
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["version", "code"], name="uniq_stage_version_code"),
            models.UniqueConstraint(fields=["version", "order"], name="uniq_stage_version_order"),
        ]
        indexes = [
            models.Index(fields=["version", "is_active", "order"], name="stage_version_active_order_idx"),
            models.Index(fields=["exam", "is_active"], name="stage_exam_active_idx"),
        ]

    def __str__(self):
        return f"{self.version} - {self.name}"
