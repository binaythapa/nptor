# organizations/models/access.py

from django.db import models
from django.contrib.auth.models import User


class ResourceAccess(models.Model):

    RESOURCE_TYPE_CHOICES = (
        ("course", "Course"),
        ("track", "Exam Track"),
        ("exam", "Exam"),
    )

    ACCESS_SOURCE_CHOICES = (
        ("public", "Public"),
        ("individual", "Individual Purchase"),
        ("organization", "Organization Assignment"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES
    )

    # ---------------- RESOURCES ----------------

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

    # ---------------- SOURCE ----------------

    source = models.CharField(
        max_length=20,
        choices=ACCESS_SOURCE_CHOICES
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    granted_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            "user",
            "resource_type",
            "course",
            "track",
            "exam",
            "source",
            "organization",
        )

    def __str__(self):

        if self.resource_type == "course" and self.course:
            resource = self.course

        elif self.resource_type == "track" and self.track:
            resource = self.track

        elif self.resource_type == "exam" and self.exam:
            resource = self.exam

        else:
            resource = "Unknown"

        return f"{self.user} → {resource} ({self.source})"