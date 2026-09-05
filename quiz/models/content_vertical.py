from django.db import models


class ContentVertical(models.Model):
    """Top-level catalog type used to classify NPTOR learning products."""

    PROFESSIONAL_CERTIFICATION = "professional_certification"
    GOVERNMENT_EXAM = "government_exam"
    ACADEMIC_EXAM = "academic_exam"
    SKILL_ASSESSMENT = "skill_assessment"

    TYPE_CHOICES = (
        (PROFESSIONAL_CERTIFICATION, "Professional Certification"),
        (GOVERNMENT_EXAM, "Government / Competitive Exam"),
        (ACADEMIC_EXAM, "Academic Exam"),
        (SKILL_ASSESSMENT, "Skill Assessment"),
    )

    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=60, unique=True)
    vertical_type = models.CharField(max_length=40, choices=TYPE_CHOICES, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["vertical_type", "is_active"], name="vertical_type_active_idx")]

    def __str__(self):
        return self.name
