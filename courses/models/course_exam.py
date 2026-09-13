from django.core.exceptions import ValidationError
from django.db import models


class CourseExam(models.Model):
    """Join a reusable Exam to a Course.

    The same exam may be used by many courses. Course-specific ordering and
    required status live on this relationship rather than on the exam itself.
    """

    course = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="course_exams",
    )
    exam = models.ForeignKey(
        "quiz.Exam",
        on_delete=models.CASCADE,
        related_name="course_memberships",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Position of this exam in the course.",
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether students must complete this exam as part of the course.",
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "exam"],
                name="unique_course_exam",
            ),
        ]
        indexes = [
            models.Index(fields=["course", "order"], name="course_exam_order_idx"),
            models.Index(fields=["exam"], name="course_exam_exam_idx"),
        ]

    def clean(self):
        super().clean()
        if self.course_id and self.exam_id:
            course = self.course
            exam = self.exam
            if (
                course.organization_id is not None
                and exam.organization_id is not None
                and course.organization_id != exam.organization_id
            ):
                raise ValidationError(
                    {"exam": "Course and exam must belong to the same organization."}
                )

    def __str__(self):
        return f"{self.course} → {self.exam}"
