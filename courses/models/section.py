from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from ckeditor.fields import RichTextField

from quiz.models import *
from .course import *


from django.db import models
from django.db.models import Max, F
from django.core.exceptions import ValidationError

from .course import Course


# =====================================================
# COURSE SECTION
# =====================================================
from django.db import models
from .course import Course
class CourseSection(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    title = models.CharField(max_length=255)

    order = models.PositiveIntegerField()

    is_deleted = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_course_section_order"
            )
        ]
        indexes = [
            models.Index(fields=["course", "order"]),
        ]

    # -------------------------
    # Validation
    # -------------------------
    def clean(self):
    # Skip validation if course is not saved yet
        if not self.course_id:
            return

        if CourseSection.objects.filter(
            course_id=self.course_id,
            order=self.order,
            is_deleted=False
        ).exclude(pk=self.pk).exists():
         raise ValidationError("This order number is already used.")

    '''
    def clean(self):
        if self.order is None:
            raise ValidationError("Order is required.")

        if CourseSection.objects.filter(
            course=self.course,
            order=self.order,
            is_deleted=False
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {"order": "This order number is already used."}
            )
    '''
    # -------------------------
    # Save override (safe)
    # -------------------------
    def save(self, *args, **kwargs):

        # Auto-assign order if not provided
        if not self.order:
            max_order = CourseSection.objects.filter(
                course=self.course,
                is_deleted=False
            ).aggregate(models.Max("order"))["order__max"] or 0

            self.order = max_order + 1

        self.full_clean()  # Run clean() before saving

        super().save(*args, **kwargs)

    # -------------------------
    # Soft delete
    # -------------------------
    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

    def __str__(self):
        return f"{self.course.title} → {self.title}"
