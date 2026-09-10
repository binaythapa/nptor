from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .organization import Organization
from .student import OrganizationStudent


class AcademicYear(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="academic_years")
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="org_academic_year_unique"),
        ]
        ordering = ["-start_date", "name"]

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("Academic year end date must be after its start date.")

    def __str__(self):
        return f"{self.organization.name}: {self.name}"


class OrganizationClass(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="classes")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="org_class_name_unique"),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClassSection(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="class_sections")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="sections")
    class_group = models.ForeignKey(OrganizationClass, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "class_group", "name"], name="academic_section_unique"),
        ]
        ordering = ["class_group__name", "name"]

    def clean(self):
        if self.academic_year_id and self.organization_id and self.academic_year.organization_id != self.organization_id:
            raise ValidationError("Academic year must belong to the same organization as the section.")
        if self.class_group_id and self.organization_id and self.class_group.organization_id != self.organization_id:
            raise ValidationError("Class must belong to the same organization as the section.")

    def __str__(self):
        return f"{self.class_group.name} - {self.name} ({self.academic_year.name})"


class StudentEnrollment(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_TRANSFERRED = "transferred"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_TRANSFERRED, "Transferred"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    )

    student = models.ForeignKey(OrganizationStudent, on_delete=models.CASCADE, related_name="enrollments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="enrollments")
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="enrollments")
    roll_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "academic_year", "status"], name="student_enrollment_status_idx"),
            models.Index(fields=["class_section", "status"], name="section_enrollment_status_idx"),
        ]

    def clean(self):
        if self.student_id and self.academic_year_id:
            if self.student.organization_id != self.academic_year.organization_id:
                raise ValidationError("Student and academic year must belong to the same organization.")
        if self.class_section_id and self.academic_year_id:
            if self.class_section.academic_year_id != self.academic_year_id:
                raise ValidationError("Enrollment section must belong to the selected academic year.")
        if self.student_id and self.class_section_id:
            if self.student.organization_id != self.class_section.organization_id:
                raise ValidationError("Student and class section must belong to the same organization.")

    def __str__(self):
        return f"{self.student.display_name}: {self.class_section}"


class ClassTeacher(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="class_teachers")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_class_teachings")
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="teacher_assignments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="teacher_assignments")
    subject = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["teacher", "class_section", "subject"], name="class_teacher_subject_unique"),
        ]
        indexes = [
            models.Index(fields=["organization", "teacher", "is_active"], name="org_teacher_active_idx"),
        ]

    def clean(self):
        if self.class_section_id and self.organization_id and self.class_section.organization_id != self.organization_id:
            raise ValidationError("Class section must belong to the same organization as the teacher assignment.")
        if self.academic_year_id and self.organization_id and self.academic_year.organization_id != self.organization_id:
            raise ValidationError("Academic year must belong to the same organization as the teacher assignment.")
        if self.class_section_id and self.academic_year_id and self.class_section.academic_year_id != self.academic_year_id:
            raise ValidationError("Class section and academic year must match.")
