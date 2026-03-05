from django.db import models
from django.contrib.auth.models import User
from .organization import Organization


class ResourceAssignment(models.Model):

    RESOURCE_TYPES = (
        ("course", "Course"),
        ("track", "Exam Track"),
        ("exam", "Exam"),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="org_resource_assignments"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resource_assignments"
    )

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPES
    )

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [

            models.UniqueConstraint(
                fields=["student", "organization", "course"],
                name="unique_student_course"
            ),

            models.UniqueConstraint(
                fields=["student", "organization", "track"],
                name="unique_student_track"
            ),

            models.UniqueConstraint(
                fields=["student", "organization", "exam"],
                name="unique_student_exam"
            ),

        ]

    def __str__(self):

        if self.course:
            return f"{self.student} ← Course {self.course}"

        if self.track:
            return f"{self.student} ← Track {self.track}"

        if self.exam:
            return f"{self.student} ← Exam {self.exam}"

        return f"{self.student} ← Resource"