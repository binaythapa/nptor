from django.conf import settings
from django.db import models

from cv.models import CareerProfile


class CVImport(models.Model):
    STATUS_REVIEW = "review"
    STATUS_CONFIRMED = "confirmed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_REVIEW, "Review"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_FAILED, "Failed"),
    )

    SOURCE_PDF = "pdf"
    SOURCE_DOCX = "docx"
    SOURCE_CHOICES = ((SOURCE_PDF, "PDF"), (SOURCE_DOCX, "DOCX"))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_imports")
    profile = models.ForeignKey(CareerProfile, on_delete=models.CASCADE, related_name="imports")
    source_file = models.FileField(upload_to="cv/imports/")
    original_filename = models.CharField(max_length=255)
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REVIEW)
    extracted_text = models.TextField(blank=True)
    parsed_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "status"], name="cv_import_owner_status_idx")]

    def __str__(self):
        return f"{self.original_filename} ({self.owner.get_username()})"


class ImportedField(models.Model):
    """One extracted fact awaiting explicit user confirmation."""

    SECTION_CHOICES = (
        ("contact", "Contact"),
        ("summary", "Summary"),
        ("experience", "Experience"),
        ("education", "Education"),
        ("skills", "Skills"),
        ("projects", "Projects"),
        ("certifications", "Certifications"),
        ("achievements", "Achievements"),
    )

    cv_import = models.ForeignKey(CVImport, on_delete=models.CASCADE, related_name="fields")
    section = models.CharField(max_length=30, choices=SECTION_CHOICES)
    field_name = models.CharField(max_length=100)
    value = models.TextField(blank=True)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_cv_import_fields",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["section", "field_name", "id"]
        indexes = [
            models.Index(fields=["cv_import", "confirmed"], name="cv_imp_field_review_idx"),
        ]

    def __str__(self):
        return f"{self.field_name}: {self.value[:60]}"
