# organizations/models/access.py
from django.db import models
from django.contrib.auth.models import User


class CourseAccess(models.Model):
    ACCESS_SOURCE_CHOICES = (
        ("public", "Public"),
        ("individual", "Individual Purchase"),
        ("organization", "Organization Assignment"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE)

    source = models.CharField(max_length=20, choices=ACCESS_SOURCE_CHOICES)
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "course", "source", "organization")

    def __str__(self):
        return f"{self.user} access to {self.course} via {self.source}"
