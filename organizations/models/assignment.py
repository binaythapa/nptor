from django.db import models
from django.contrib.auth.models import User
from .organization import Organization
from .membership import OrganizationGroup


class ResourceAssignment(models.Model):

    RESOURCE_TYPES = (
        ("course", "Course"),
        ("track", "Exam Track"),
        ("exam", "Exam"),
    )

    # =========================
    # TARGET (INDIVIDUAL / GROUP)
    # =========================

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="org_resource_assignments",
        null=True,
        blank=True
    )

    group = models.ForeignKey(
        OrganizationGroup,
        on_delete=models.CASCADE,
        related_name="resource_assignments",
        null=True,
        blank=True
    )

    # =========================
    # ORGANIZATION
    # =========================

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="resource_assignments"
    )

    # =========================
    # RESOURCE TYPE
    # =========================

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPES
    )

    # =========================
    # RESOURCES
    # =========================

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

    # =========================
    # VALIDATION
    # =========================

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.student and not self.group:
            raise ValidationError("Either student or group must be set.")

        if self.student and self.group:
            raise ValidationError("Cannot assign to both student and group.")

    # =========================
    # CONSTRAINTS
    # =========================

    class Meta:
        constraints = [

            # ---------- INDIVIDUAL ----------
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

            # ---------- GROUP ----------
            models.UniqueConstraint(
                fields=["group", "organization", "course"],
                name="unique_group_course"
            ),
            models.UniqueConstraint(
                fields=["group", "organization", "track"],
                name="unique_group_track"
            ),
            models.UniqueConstraint(
                fields=["group", "organization", "exam"],
                name="unique_group_exam"
            ),
        ]

    # =========================
    # STRING REPRESENTATION
    # =========================

    def __str__(self):

        target = self.student or self.group

        if self.course:
            return f"{target} ← Course {self.course}"

        if self.track:
            return f"{target} ← Track {self.track}"

        if self.exam:
            return f"{target} ← Exam {self.exam}"

        return f"{target} ← Resource"