from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .academic import ClassSection
from .organization import Organization


class ClassResourceAssignment(models.Model):
    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"
    RESOURCE_TYPES = ((RESOURCE_COURSE, "Course"), (RESOURCE_TRACK, "Exam Track"), (RESOURCE_EXAM, "Exam"))

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="class_resource_assignments")
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="resource_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="class_resource_assignments_created")
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    course = models.ForeignKey("courses.Course", null=True, blank=True, on_delete=models.PROTECT, related_name="class_resource_assignments")
    track = models.ForeignKey("quiz.ExamTrack", null=True, blank=True, on_delete=models.PROTECT, related_name="class_resource_assignments")
    exam = models.ForeignKey("quiz.Exam", null=True, blank=True, on_delete=models.PROTECT, related_name="class_resource_assignments")
    starts_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["class_section", "resource_type", "course", "track", "exam"], name="class_resource_assignment_unique")]
        indexes = [models.Index(fields=["organization", "class_section", "is_active"], name="class_res_assign_scope_idx")]

    def clean(self):
        if self.class_section_id and self.organization_id and self.class_section.organization_id != self.organization_id:
            raise ValidationError("Class section must belong to the same organization.")
        selected = [self.course_id, self.track_id, self.exam_id]
        if sum(value is not None for value in selected) != 1:
            raise ValidationError("Exactly one learning resource must be selected.")
        expected = {self.RESOURCE_COURSE: self.course_id, self.RESOURCE_TRACK: self.track_id, self.RESOURCE_EXAM: self.exam_id}.get(self.resource_type)
        if expected is None:
            raise ValidationError("Resource type and resource must match.")
        if self.starts_at and self.due_at and self.due_at < self.starts_at:
            raise ValidationError("Due date cannot be earlier than the start date.")
        if self.due_at and self.expires_at and self.expires_at < self.due_at:
            raise ValidationError("Expiration cannot be earlier than the due date.")

    @property
    def resource(self):
        return {self.RESOURCE_COURSE: self.course, self.RESOURCE_TRACK: self.track, self.RESOURCE_EXAM: self.exam}.get(self.resource_type)
