# organizations/models/assignment.py
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ResourceAssignment(models.Model):
    """
    Represents an organization's assignment of a learning resource
    to a student.

    Supported resources:

        - Course
        - Exam Track
        - Exam

    ResourceAssignment is the BUSINESS/AUDIT record.

    ResourceAccess is responsible for actual access authorization.

    Example:

        Organization
            |
            +-- Teacher
            |
            +-- Student
                    |
                    +-- Course assignment
                    +-- Exam Track assignment
                    +-- Exam assignment

    A student may receive the same resource more than once over time.
    Historical assignments are therefore preserved.

    Organization isolation:

        - Student must belong to the organization.
        - assigned_by must belong to the organization.
        - assigned_by must be an organization admin or staff member.
    """

    # =========================================================
    # RESOURCE TYPES
    # =========================================================

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPES = (
        (
            RESOURCE_COURSE,
            "Course",
        ),
        (
            RESOURCE_TRACK,
            "Exam Track",
        ),
        (
            RESOURCE_EXAM,
            "Exam",
        ),
    )

    # =========================================================
    # STATUS
    # =========================================================

    STATUS_ASSIGNED = "assigned"
    STATUS_STARTED = "started"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_REVOKED = "revoked"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (
            STATUS_ASSIGNED,
            "Assigned",
        ),
        (
            STATUS_STARTED,
            "Started",
        ),
        (
            STATUS_COMPLETED,
            "Completed",
        ),
        (
            STATUS_EXPIRED,
            "Expired",
        ),
        (
            STATUS_REVOKED,
            "Revoked",
        ),
        (
            STATUS_CANCELLED,
            "Cancelled",
        ),
    )

    # =========================================================
    # IDENTIFIER
    # =========================================================

   



    assignment_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Unique identifier for this assignment.",
    )

    # =========================================================
    # ORGANIZATION
    # =========================================================

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="resource_assignments",
    )

    # =========================================================
    # STUDENT
    # =========================================================

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="org_resource_assignments",
    )

    # =========================================================
    # ASSIGNED BY
    # =========================================================

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resource_assignments_created",
        help_text=(
            "Organization admin or staff member who "
            "created the assignment."
        ),
    )

    # =========================================================
    # RESOURCE TYPE
    # =========================================================

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPES,
        db_index=True,
    )

    # =========================================================
    # RESOURCES
    # =========================================================

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="organization_assignments",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="organization_assignments",
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="organization_assignments",
    )

    # =========================================================
    # LIFECYCLE
    # =========================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ASSIGNED,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Controls whether this assignment is currently active."
        ),
    )

    # =========================================================
    # TIMELINE
    # =========================================================

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    starts_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "When the student becomes eligible to access "
            "the assigned resource."
        ),
    )

    due_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Optional deadline for completing the assignment."
        ),
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "When access to the assigned resource expires."
        ),
    )

    # =========================================================
    # COMPLETION
    # =========================================================

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # REVOCATION
    # =========================================================

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resource_assignments_revoked",
    )

    revoke_reason = models.TextField(
        blank=True,
    )

    # =========================================================
    # NOTES
    # =========================================================

    notes = models.TextField(
        blank=True,
        help_text=(
            "Optional internal note about this assignment."
        ),
    )

    # =========================================================
    # AUDIT
    # =========================================================

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = [
            "-assigned_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "student",
                    "is_active",
                ],
                name="res_assign_org_stu_idx",
            ),

            models.Index(
                fields=[
                    "organization",
                    "resource_type",
                    "is_active",
                ],
                name="res_assign_org_type_idx",
            ),

            models.Index(
                fields=[
                    "student",
                    "resource_type",
                    "is_active",
                ],
                name="res_assign_stu_type_idx",
            ),

            models.Index(
                fields=[
                    "organization",
                    "status",
                ],
                name="res_assign_org_status_idx",
            ),

            models.Index(
                fields=[
                    "due_at",
                    "is_active",
                ],
                name="res_assign_due_idx",
            ),

            models.Index(
                fields=[
                    "expires_at",
                    "is_active",
                ],
                name="res_assign_exp_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        """
        Validate assignment integrity.

        Important:
        This validates model-level data integrity.

        Authorization and business workflows should still be
        enforced by the Organization service/permission layer.
        """

        super().clean()

        errors = {}

        # =====================================================
        # ORGANIZATION
        # =====================================================

        if not self.organization_id:
            errors["organization"] = (
                "An organization is required."
            )

        # =====================================================
        # STUDENT
        # =====================================================

        if not self.student_id:
            errors["student"] = (
                "A student is required."
            )

        # =====================================================
        # ASSIGNED BY
        # =====================================================

        if self.assigned_by_id:

            if self.assigned_by_id == self.student_id:
                errors["assigned_by"] = (
                    "The assigned_by user cannot be "
                    "the assigned student."
                )

        # =====================================================
        # RESOURCE TYPE
        # =====================================================

        resource_map = {
            self.RESOURCE_COURSE: self.course_id,
            self.RESOURCE_TRACK: self.track_id,
            self.RESOURCE_EXAM: self.exam_id,
        }

        if self.resource_type not in resource_map:
            errors["resource_type"] = (
                "Invalid resource type."
            )

        else:

            selected_resources = [
                self.course_id,
                self.track_id,
                self.exam_id,
            ]

            selected_count = sum(
                value is not None
                for value in selected_resources
            )

            # Exactly one resource must be selected.
            if selected_count != 1:
                errors["resource_type"] = (
                    "Exactly one resource must be assigned."
                )

            expected_resource_id = resource_map[
                self.resource_type
            ]

            if expected_resource_id is None:
                errors["resource_type"] = (
                    f"A {self.resource_type} must be "
                    "selected for this resource type."
                )

            # -------------------------------------------------
            # Ensure unrelated resources are empty.
            # -------------------------------------------------

            if self.resource_type == self.RESOURCE_COURSE:

                if self.track_id or self.exam_id:
                    errors["resource_type"] = (
                        "Course assignments cannot contain "
                        "a track or exam."
                    )

            elif self.resource_type == self.RESOURCE_TRACK:

                if self.course_id or self.exam_id:
                    errors["resource_type"] = (
                        "Track assignments cannot contain "
                        "a course or exam."
                    )

            elif self.resource_type == self.RESOURCE_EXAM:

                if self.course_id or self.track_id:
                    errors["resource_type"] = (
                        "Exam assignments cannot contain "
                        "a course or track."
                    )

        # =====================================================
        # TIMELINE
        # =====================================================

        if self.starts_at and self.due_at:

            if self.due_at < self.starts_at:
                errors["due_at"] = (
                    "Due date cannot be earlier than "
                    "the start date."
                )

        if self.starts_at and self.expires_at:

            if self.expires_at < self.starts_at:
                errors["expires_at"] = (
                    "Expiration cannot be earlier than "
                    "the start date."
                )

        if self.due_at and self.expires_at:

            if self.expires_at < self.due_at:
                errors["expires_at"] = (
                    "Expiration cannot be earlier than "
                    "the due date."
                )

        # =====================================================
        # COMPLETION
        # =====================================================

        if (
            self.status == self.STATUS_COMPLETED
            and not self.completed_at
        ):
            errors["completed_at"] = (
                "Completed assignments must have "
                "a completed_at timestamp."
            )

        if (
            self.completed_at
            and self.status != self.STATUS_COMPLETED
        ):
            errors["status"] = (
                "completed_at can only be set when "
                "the assignment status is completed."
            )

        # =====================================================
        # REVOCATION
        # =====================================================

        if self.status == self.STATUS_REVOKED:

            if not self.revoked_at:
                errors["revoked_at"] = (
                    "Revoked assignments must have "
                    "a revoked_at timestamp."
                )

        if (
            self.revoked_at
            and self.status != self.STATUS_REVOKED
        ):
            errors["status"] = (
                "revoked_at can only be set when "
                "the assignment is revoked."
            )

        if self.revoked_by_id and not self.revoked_at:
            errors["revoked_at"] = (
                "revoked_by requires revoked_at."
            )

        # =====================================================
        # ACTIVE STATE
        # =====================================================

        inactive_statuses = {
            self.STATUS_EXPIRED,
            self.STATUS_REVOKED,
            self.STATUS_CANCELLED,
        }

        if (
            self.status in inactive_statuses
            and self.is_active
        ):
            errors["is_active"] = (
                "Expired, revoked, or cancelled "
                "assignments cannot be active."
            )

        if errors:
            raise ValidationError(errors)

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):
        """
        Apply lifecycle defaults before saving.

        UUID assignment_key is generated automatically by the
        field default.

        Expired assignments are automatically deactivated when
        their expiration time has passed.
        """

        now = timezone.now()

        # -----------------------------------------------------
        # Automatically expire active assignments.
        # -----------------------------------------------------

        if (
            self.expires_at
            and self.expires_at <= now
            and self.status
            not in {
                self.STATUS_COMPLETED,
                self.STATUS_REVOKED,
                self.STATUS_CANCELLED,
            }
        ):
            self.status = self.STATUS_EXPIRED
            self.is_active = False

        # -----------------------------------------------------
        # Revoked assignments are always inactive.
        # -----------------------------------------------------

        if self.status == self.STATUS_REVOKED:

            self.is_active = False

            if not self.revoked_at:
                self.revoked_at = now

        # -----------------------------------------------------
        # Cancelled assignments are always inactive.
        # -----------------------------------------------------

        if self.status == self.STATUS_CANCELLED:
            self.is_active = False

        # -----------------------------------------------------
        # Expired assignments are always inactive.
        # -----------------------------------------------------

        if self.status == self.STATUS_EXPIRED:
            self.is_active = False

        # -----------------------------------------------------
        # Completed assignments remain historically visible,
        # but are no longer active.
        # -----------------------------------------------------

        if self.status == self.STATUS_COMPLETED:
            self.is_active = False

            if not self.completed_at:
                self.completed_at = now

        super().save(*args, **kwargs)

    # =========================================================
    # RESOURCE HELPERS
    # =========================================================

    @property
    def resource(self):
        """
        Return the assigned resource object.

        Only one of course, track, or exam should exist.
        """

        if self.resource_type == self.RESOURCE_COURSE:
            return self.course

        if self.resource_type == self.RESOURCE_TRACK:
            return self.track

        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam

        return None

    @property
    def resource_name(self):
        """
        Human-readable resource name.
        """

        resource = self.resource

        if resource is None:
            return None

        return str(resource)

    # =========================================================
    # STATUS HELPERS
    # =========================================================

    @property
    def is_completed(self):
        return (
            self.status == self.STATUS_COMPLETED
        )

    @property
    def is_expired(self):
        if self.status == self.STATUS_EXPIRED:
            return True

        if (
            self.expires_at
            and self.expires_at <= timezone.now()
        ):
            return True

        return False

    @property
    def is_revoked(self):
        return (
            self.status == self.STATUS_REVOKED
        )

    @property
    def is_cancelled(self):
        return (
            self.status == self.STATUS_CANCELLED
        )

    @property
    def has_started(self):
        return (
            self.status == self.STATUS_STARTED
            or self.completed_at is not None
        )

    @property
    def is_available_now(self):
        """
        Whether the assignment is currently within its
        allowed timeline.

        This does NOT replace ResourceAccess authorization.
        """

        if not self.is_active:
            return False

        now = timezone.now()

        if self.starts_at and now < self.starts_at:
            return False

        if self.expires_at and now >= self.expires_at:
            return False

        if self.status in {
            self.STATUS_EXPIRED,
            self.STATUS_REVOKED,
            self.STATUS_CANCELLED,
        }:
            return False

        return True

    @property
    def is_overdue(self):
        """
        Whether the assignment has passed its due date without
        being completed.
        """

        if self.is_completed:
            return False

        if not self.due_at:
            return False

        return timezone.now() > self.due_at

    # =========================================================
    # STATE TRANSITIONS
    # =========================================================

    def mark_started(self):
        """
        Mark an assigned resource as started.
        """

        if self.status in {
            self.STATUS_REVOKED,
            self.STATUS_CANCELLED,
            self.STATUS_EXPIRED,
            self.STATUS_COMPLETED,
        }:
            return False

        self.status = self.STATUS_STARTED
        self.is_active = True
        self.save(
            update_fields=[
                "status",
                "is_active",
                "updated_at",
            ]
        )

        return True

    def mark_completed(self, completed_at=None):
        """
        Mark assignment as completed.
        """

        if self.status in {
            self.STATUS_REVOKED,
            self.STATUS_CANCELLED,
        }:
            return False

        self.status = self.STATUS_COMPLETED
        self.is_active = False
        self.completed_at = (
            completed_at or timezone.now()
        )

        self.save(
            update_fields=[
                "status",
                "is_active",
                "completed_at",
                "updated_at",
            ]
        )

        return True

    def revoke(
        self,
        revoked_by=None,
        reason="",
        revoked_at=None,
    ):
        """
        Revoke the assignment.
        """

        self.status = self.STATUS_REVOKED
        self.is_active = False
        self.revoked_at = (
            revoked_at or timezone.now()
        )
        self.revoked_by = revoked_by
        self.revoke_reason = reason or ""

        self.save(
            update_fields=[
                "status",
                "is_active",
                "revoked_at",
                "revoked_by",
                "revoke_reason",
                "updated_at",
            ]
        )

        return True

    def cancel(self):
        """
        Cancel the assignment.
        """

        if self.status in {
            self.STATUS_COMPLETED,
            self.STATUS_REVOKED,
        }:
            return False

        self.status = self.STATUS_CANCELLED
        self.is_active = False

        self.save(
            update_fields=[
                "status",
                "is_active",
                "updated_at",
            ]
        )

        return True

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        resource_name = self.resource_name or "Resource"

        return (
            f"{self.student} ← "
            f"{resource_name} "
            f"({self.get_status_display()})"
        )