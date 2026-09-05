from django.db import models

from courses.models import Course

from .content_vertical import ContentVertical
from .country import Country
from .exam import Exam


class PreparationProgram(models.Model):
    """Reusable preparation context for academic, entrance, certification and other programs."""

    content_vertical = models.ForeignKey(
        ContentVertical,
        on_delete=models.PROTECT,
        related_name="preparation_programs",
    )
    country = models.ForeignKey(
        Country,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="preparation_programs",
    )
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=140)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True)
    official_website = models.URLField(blank=True)

    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name="preparation_programs",
    )
    exams = models.ManyToManyField(
        Exam,
        blank=True,
        related_name="preparation_programs",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_vertical", "code"],
                name="uniq_prep_program_vertical_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["content_vertical", "is_active"],
                name="prep_program_vertical_active_idx",
            ),
            models.Index(
                fields=["country", "is_active"],
                name="prep_program_country_active_idx",
            ),
            models.Index(
                fields=["is_published", "is_active"],
                name="prep_program_published_active_idx",
            ),
        ]

    def __str__(self):
        return self.name
