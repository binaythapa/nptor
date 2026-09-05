from django.db import models

from cv.models_version import CVVersion


class DocumentArtifact(models.Model):
    PDF = "pdf"
    DOCX = "docx"
    TYPE_CHOICES = ((PDF, "PDF"), (DOCX, "DOCX"))

    cv_version = models.ForeignKey(CVVersion, on_delete=models.CASCADE, related_name="artifacts")
    artifact_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    file = models.FileField(upload_to="cv/artifacts/")
    mime_type = models.CharField(max_length=150)
    template_slug = models.CharField(max_length=100)
    template_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["cv_version", "artifact_type"], name="cv_artifact_type_idx")]

    def __str__(self):
        return f"{self.cv_version} {self.artifact_type}"
