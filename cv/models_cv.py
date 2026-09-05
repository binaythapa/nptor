from django.conf import settings
from django.db import models

from cv.models import CareerProfile
from cv.models_template import CVTemplate


class CV(models.Model):
    """A saved, independently editable CV owned by an NPTOR account."""

    STATUS_DRAFT = "draft"
    STATUS_COMPLETED = "completed"
    STATUS_FINAL = "final"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FINAL, "Final"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cvs",
    )
    profile = models.ForeignKey(
        CareerProfile,
        on_delete=models.CASCADE,
        related_name="cvs",
    )
    template = models.ForeignKey(
        CVTemplate,
        on_delete=models.PROTECT,
        related_name="cvs",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    selected_sections = models.JSONField(default=dict, blank=True)
    overrides = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "status"], name="cv_owner_status_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.owner.get_username()})"
