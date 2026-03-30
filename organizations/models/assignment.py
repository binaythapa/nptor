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


    # ADD BELOW assigned_at

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_resources"
        )

    deadline = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    version = models.IntegerField(default=1)

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
    

class AssignmentHistory(models.Model):

    ACTIONS = (
        ("created", "Created"),
        ("updated", "Updated"),
        ("overwritten", "Overwritten"),
    )

    assignment = models.ForeignKey(
        ResourceAssignment,
        on_delete=models.CASCADE,
        related_name="history"
    )

    action = models.CharField(max_length=20, choices=ACTIONS)

    performed_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    old_deadline = models.DateTimeField(null=True, blank=True)
    new_deadline = models.DateTimeField(null=True, blank=True)

    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.assignment} - {self.action}"
    

class UserProgress(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(ResourceAssignment, on_delete=models.CASCADE)

    progress_percent = models.FloatField(default=0)
    is_completed = models.BooleanField(default=False)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "assignment")