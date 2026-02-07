# organizations/models/assignment.py
from django.db import models
from django.contrib.auth.models import User
from .organization import Organization


class CourseAssignment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="org_course_assignments"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="course_assignments"
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="assigned_by_orgs"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "organization", "course")

    def __str__(self):
        return f"{self.student} ← {self.course} ({self.organization})"
