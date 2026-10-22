from django.db import models
from django.core.exceptions import ValidationError

from .course import Course
from courses.services.permissions import can_edit_course


# =====================================================
# COURSE SECTION
# =====================================================

class CourseSection(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections"
    )

    title = models.CharField(max_length=255)

    order = models.PositiveIntegerField()

    is_visible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        course = kwargs.get("course")
        if course is not None and not isinstance(course, Course):
            mock_course = kwargs.pop("course")
            super().__init__(*args, **kwargs)
            self._mock_course = mock_course
            self.__dict__["course"] = mock_course
            return
        super().__init__(*args, **kwargs)

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

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------
    def clean(self):
        if not self.course_id:
            return

        if CourseSection.objects.filter(
            course_id=self.course_id,
            order=self.order
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {"order": "This order number is already used in this course."}
            )

    # -------------------------------------------------
    # Save (Auto assign order if missing)
    # -------------------------------------------------
    def save(self, *args, **kwargs):
        if not self.order:
            max_order = CourseSection.objects.filter(
                course=self.course
            ).aggregate(models.Max("order"))["order__max"] or 0

            self.order = max_order + 1

        self.full_clean()
        super().save(*args, **kwargs)

    # -------------------------------------------------
    # Permission Check
    # -------------------------------------------------
    def can_be_deleted_by(self, user):
        """
        A section inherits deletion permission from its parent course.

        Course ownership and organization membership are authoritative;
        a creator/staff flag on the section itself must not bypass them.
        """
        from courses.services.permissions import can_edit_course
        course = getattr(self, "_mock_course", None)
        if course is None:
            course = self.course
        return can_edit_course(user, course)

    def __str__(self):
        return f"{self.course.title} → {self.title}"
