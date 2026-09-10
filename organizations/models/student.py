from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .organization import Organization


class OrganizationStudent(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_GRADUATED = "graduated"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_GRADUATED, "Graduated"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="students")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_student_records")
    student_id = models.CharField(max_length=100, blank=True)
    admission_no = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    guardian_name = models.CharField(max_length=255, blank=True)
    guardian_phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    joined_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="org_student_user_unique"),
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="org_student_status_idx"),
            models.Index(fields=["organization", "student_id"], name="org_student_id_idx"),
        ]

    def clean(self):
        if not self.organization_id or not self.user_id:
            return
        from .membership import OrganizationMember
        if not OrganizationMember.objects.filter(
            organization_id=self.organization_id,
            user_id=self.user_id,
            role="student",
            is_active=True,
        ).exists():
            raise ValidationError("An OrganizationStudent requires an active student membership in the same organization.")

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.get_username()

    def __str__(self):
        return f"{self.display_name} @ {self.organization.name}"


class Guardian(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="guardians")
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    relationship = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "name"], name="org_guardian_name_idx")]

    def __str__(self):
        return self.name


class StudentGuardian(models.Model):
    student = models.ForeignKey(OrganizationStudent, on_delete=models.CASCADE, related_name="guardian_links")
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name="student_links")
    is_primary = models.BooleanField(default=False)
    can_receive_notifications = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "guardian"], name="student_guardian_unique"),
        ]

    def clean(self):
        if self.student_id and self.guardian_id:
            if self.student.organization_id != self.guardian.organization_id:
                raise ValidationError("Student and guardian must belong to the same organization.")
