from django.db import models

from cv.models_cv import CV


class CVVersion(models.Model):
    """Immutable snapshot of a saved CV at a point in time."""

    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cv", "version_number"],
                name="uniq_cv_version_number",
            )
        ]

    def __str__(self):
        return f"{self.cv.title} v{self.version_number}"
