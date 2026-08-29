# organizations/services/assignments.py

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember

from courses.models import Course
from quiz.models import Exam, ExamTrack


# ============================================================
# EXCEPTIONS
# ============================================================
class AssignmentError(Exception):
    """Base exception for assignment service errors."""


class InvalidAssignmentError(AssignmentError):
    """Raised when assignment data is invalid."""
    pass


class StudentNotInOrganizationError(AssignmentError):
    """
    Raised when the selected student is not an active member
    of the organization.
    """
    pass


class DuplicateActiveAssignmentError(AssignmentError):
    """Raised when an active assignment already exists."""
    pass


class ResourceNotAvailableError(AssignmentError):
    """
    Raised when a resource does not exist or is not available
    to the current organization.
    """
    pass


class UnauthorizedAssignmentError(AssignmentError):
    """
    Raised when the current user is not authorized to perform
    an assignment operation.
    """
    pass


class AssignmentPermissionError(AssignmentError):
    """
    Raised when the actor does not have sufficient permissions.
    """
    pass


# Backward-compatible aliases.
AssignmentValidationError = InvalidAssignmentError
AssignmentDuplicateError = DuplicateActiveAssignmentError
AssignmentNotFoundError = ResourceNotAvailableError



# ============================================================
# ASSIGNMENT RESULT
# ============================================================


@dataclass
class AssignmentResult:
    """
    Result returned by assign_resource().
    """

    assignment: ResourceAssignment
    access: ResourceAccess
    created: bool

# ============================================================
# INTERNAL VALIDATION
# ============================================================


def _validate_actor(
    *,
    actor,
    organization,
):
    """
    Validate the user performing the operation.

    The actor must:
        - be authenticated
        - be an active organization member
        - have student-management capability
    """

    if actor is None:
        raise AssignmentPermissionError(
            "An authenticated actor is required."
        )

    if not actor.is_authenticated:
        raise AssignmentPermissionError(
            "Authentication is required."
        )

    membership = (
        OrganizationMember.objects
        .filter(
            user=actor,
            organization=organization,
            is_active=True,
        )
        .first()
    )

    if not membership:
        raise AssignmentPermissionError(
            "You are not an active member of this organization."
        )

    if not membership.can_manage_students:
        raise UnauthorizedAssignmentError(
            "You do not have permission to manage student assignments."
        )

    return membership


def _validate_student(
    *,
    student,
    organization,
):
    """
    Ensure the target user is an active student of the
    same organization.
    """

    membership = (
        OrganizationMember.objects
        .filter(
            user=student,
            organization=organization,
            role=OrganizationMember.ROLE_STUDENT,
            is_active=True,
        )
        .first()
    )

    if not membership:
        raise StudentNotInOrganizationError(
            "The selected user is not an active student "
            "of this organization."
        )

    return membership


def _validate_dates(
    *,
    starts_at: Optional[datetime] = None,
    due_at: Optional[datetime] = None,
    expires_at: Optional[datetime] = None,
):
    """
    Validate assignment lifecycle dates.
    """

    if starts_at and due_at and due_at <= starts_at:
        raise AssignmentValidationError(
            "The due date must be later than the start date."
        )

    if starts_at and expires_at and expires_at <= starts_at:
        raise AssignmentValidationError(
            "The expiration date must be later than the start date."
        )

    if due_at and expires_at and expires_at < due_at:
        raise AssignmentValidationError(
            "The expiration date cannot be earlier than the due date."
        )


# ============================================================
# RESOURCE FILTER
# ============================================================


def _resource_filter(
    *,
    resource_type,
    resource,
):
    """
    Return the ResourceAssignment / ResourceAccess field
    corresponding to the resource type.
    """

    if resource_type == ResourceAssignment.RESOURCE_COURSE:
        return {"course": resource}

    if resource_type == ResourceAssignment.RESOURCE_TRACK:
        return {"track": resource}

    if resource_type == ResourceAssignment.RESOURCE_EXAM:
        return {"exam": resource}

    raise AssignmentValidationError(
        "Unsupported resource type."
    )


# ============================================================
# RESOURCE RESOLUTION
# ============================================================


def _get_resource(
    *,
    resource_type,
    resource_id,
    organization,
):
    """
    Resolve a resource while enforcing organization isolation.

    Courses:
        - Organization-owned courses must belong to this organization.
        - Platform courses are allowed.

    Tracks:
        - Must belong to this organization.

    Exams:
        - Must belong to this organization.
    """

    if not resource_id:
        raise AssignmentValidationError(
            "A resource ID is required."
        )

    # --------------------------------------------------------
    # COURSE
    # --------------------------------------------------------

    if resource_type == ResourceAssignment.RESOURCE_COURSE:

        resource = (
            Course.objects
            .filter(pk=resource_id)
            .first()
        )

        if not resource:
            raise ResourceNotAvailableError(
                "Course not found."
            )

        # Organization-owned course.
        if resource.organization_id is not None:

            if resource.organization_id != organization.id:
                raise ResourceNotAvailableError(
                    "This course is not available to this organization."
                )

        return resource

    # --------------------------------------------------------
    # TRACK
    # --------------------------------------------------------

    if resource_type == ResourceAssignment.RESOURCE_TRACK:

        resource = (
            ExamTrack.objects
            .filter(
                pk=resource_id,
                organization=organization,
            )
            .first()
        )

        if not resource:
            raise ResourceNotAvailableError(
                "Exam track not found or is not available "
                "to this organization."
            )

        return resource

    # --------------------------------------------------------
    # EXAM
    # --------------------------------------------------------

    if resource_type == ResourceAssignment.RESOURCE_EXAM:

        resource = (
            Exam.objects
            .filter(
                pk=resource_id,
                organization=organization,
            )
            .first()
        )

        if not resource:
            raise ResourceNotAvailableError(
                "Exam not found or is not available "
                "to this organization."
            )

        return resource

    raise AssignmentValidationError(
        "Unsupported resource type."
    )


# ============================================================
# ASSIGNMENT LOOKUPS
# ============================================================


def _find_active_assignment(
    *,
    student,
    organization,
    resource_type,
    resource,
):
    """
    Find the active assignment for an exact resource.
    """

    filters = {
        "student": student,
        "organization": organization,
        "resource_type": resource_type,
        "is_active": True,
    }

    filters.update(
        _resource_filter(
            resource_type=resource_type,
            resource=resource,
        )
    )

    return (
        ResourceAssignment.objects
        .filter(**filters)
        .first()
    )


def _find_latest_assignment(
    *,
    student,
    organization,
    resource_type,
    resource,
):
    """
    Find the latest historical assignment for the exact
    student, organization and resource.
    """

    filters = {
        "student": student,
        "organization": organization,
        "resource_type": resource_type,
    }

    filters.update(
        _resource_filter(
            resource_type=resource_type,
            resource=resource,
        )
    )

    return (
        ResourceAssignment.objects
        .filter(**filters)
        .order_by("-assigned_at")
        .first()
    )


# ============================================================
# RESOURCE ACCESS
# ============================================================


def _get_or_create_resource_access(
    *,
    student,
    organization,
    resource_type,
    resource,
    assignment,
    expires_at=None,
):
    """
    Create or reactivate the ResourceAccess record associated
    with the assignment.

    ResourceAssignment:
        Business assignment/history.

    ResourceAccess:
        Authorization/access state.
    """

    filters = {
        "user": student,
        "organization": organization,
        "resource_type": resource_type,
        "source": ResourceAccess.SOURCE_ORGANIZATION,
    }

    filters.update(
        _resource_filter(
            resource_type=resource_type,
            resource=resource,
        )
    )

    defaults = {
        "assignment": assignment,
        "is_active": True,
        "expires_at": expires_at,
    }

    access, created = (
        ResourceAccess.objects
        .get_or_create(
            **filters,
            defaults=defaults,
        )
    )

    if created:
        return access

    update_fields = []

    # --------------------------------------------------------
    # Link access to current assignment
    # --------------------------------------------------------

    if access.assignment_id != assignment.id:
        access.assignment = assignment
        update_fields.append("assignment")

    # --------------------------------------------------------
    # Reactivate access
    # --------------------------------------------------------

    if not access.is_active:
        access.is_active = True
        access.revoked_at = None

        update_fields.extend(
            [
                "is_active",
                "revoked_at",
            ]
        )

    # --------------------------------------------------------
    # Update expiration
    # --------------------------------------------------------

    if access.expires_at != expires_at:
        access.expires_at = expires_at
        update_fields.append("expires_at")

    if update_fields:
        access.save(
            update_fields=update_fields
        )

    return access


# ============================================================
# ASSIGN RESOURCE
# ============================================================


@transaction.atomic
def assign_resource(
    *,
    student,
    organization,
    resource_type,
    resource_id,
    actor,
    starts_at=None,
    due_at=None,
    expires_at=None,
    notes="",
    allow_reactivate=False,
):
    """
    Assign a course, exam track, or exam to a student.

    This is the primary service boundary for assignment
    creation.

    The service is independent of HTTP views.
    """

    # --------------------------------------------------------
    # Organization
    # --------------------------------------------------------

    if organization is None:
        raise AssignmentValidationError(
            "An organization is required."
        )

    if not organization.is_active:
        raise AssignmentValidationError(
            "Cannot create assignments for an inactive organization."
        )

    # --------------------------------------------------------
    # Actor
    # --------------------------------------------------------

    _validate_actor(
        actor=actor,
        organization=organization,
    )

    # --------------------------------------------------------
    # Student
    # --------------------------------------------------------

    _validate_student(
        student=student,
        organization=organization,
    )

    # --------------------------------------------------------
    # Resource type
    # --------------------------------------------------------

    valid_types = {
        ResourceAssignment.RESOURCE_COURSE,
        ResourceAssignment.RESOURCE_TRACK,
        ResourceAssignment.RESOURCE_EXAM,
    }

    if resource_type not in valid_types:
        raise AssignmentValidationError(
            "Invalid resource type."
        )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    _validate_dates(
        starts_at=starts_at,
        due_at=due_at,
        expires_at=expires_at,
    )

    # --------------------------------------------------------
    # Resource
    # --------------------------------------------------------

    resource = _get_resource(
        resource_type=resource_type,
        resource_id=resource_id,
        organization=organization,
    )

    # --------------------------------------------------------
    # Existing active assignment
    # --------------------------------------------------------

    active_assignment = _find_active_assignment(
        student=student,
        organization=organization,
        resource_type=resource_type,
        resource=resource,
    )

    if active_assignment:
        raise DuplicateActiveAssignmentError(
            "This resource is already assigned to this student."
        )

    # --------------------------------------------------------
    # Historical assignment
    # --------------------------------------------------------

    historical_assignment = _find_latest_assignment(
        student=student,
        organization=organization,
        resource_type=resource_type,
        resource=resource,
    )

    # --------------------------------------------------------
    # Reactivate historical assignment
    # --------------------------------------------------------

    if historical_assignment and allow_reactivate:

        assignment = historical_assignment

        assignment.assigned_by = actor
        assignment.status = ResourceAssignment.STATUS_ASSIGNED
        assignment.is_active = True

        assignment.starts_at = starts_at
        assignment.due_at = due_at
        assignment.expires_at = expires_at

        assignment.completed_at = None
        assignment.revoked_at = None
        assignment.revoked_by = None
        assignment.revoke_reason = ""
        assignment.notes = notes or ""

        assignment.save()

    # --------------------------------------------------------
    # Create new assignment
    # --------------------------------------------------------

    else:

        assignment = ResourceAssignment(
            student=student,
            organization=organization,
            assigned_by=actor,
            resource_type=resource_type,
            status=ResourceAssignment.STATUS_ASSIGNED,
            is_active=True,
            starts_at=starts_at,
            due_at=due_at,
            expires_at=expires_at,
            notes=notes or "",
        )

        if resource_type == ResourceAssignment.RESOURCE_COURSE:
            assignment.course = resource

        elif resource_type == ResourceAssignment.RESOURCE_TRACK:
            assignment.track = resource

        elif resource_type == ResourceAssignment.RESOURCE_EXAM:
            assignment.exam = resource

        assignment.save()

    # --------------------------------------------------------
    # Resource access
    # --------------------------------------------------------  

    access = _get_or_create_resource_access(
        student=student,
        organization=organization,
        resource_type=resource_type,
        resource=resource,
            assignment=assignment,
    expires_at=expires_at,
    )

    return AssignmentResult(
        assignment=assignment,
        access=access,
        created=not bool(historical_assignment and allow_reactivate),
    )


# ============================================================
# REVOKE ASSIGNMENT
# ============================================================


@transaction.atomic
def revoke_assignment(
    *,
    assignment,
    actor,
    reason="",
):
    """
    Revoke an assignment without deleting historical data.
    """

    if assignment is None:
        raise AssignmentValidationError(
            "An assignment is required."
        )

    _validate_actor(
        actor=actor,
        organization=assignment.organization,
    )

    if not assignment.is_active:
        return assignment

    now = timezone.now()

    assignment.is_active = False
    assignment.status = ResourceAssignment.STATUS_REVOKED
    assignment.revoked_at = now
    assignment.revoked_by = actor
    assignment.revoke_reason = reason or ""

    assignment.save()

    ResourceAccess.objects.filter(
        assignment=assignment,
        is_active=True,
    ).update(
        is_active=False,
        revoked_at=now,
    )

    return assignment


# ============================================================
# CANCEL ASSIGNMENT
# ============================================================


@transaction.atomic
def cancel_assignment(
    *,
    assignment,
    actor,
    reason="",
):
    """
    Cancel an assignment without deleting historical data.
    """

    if assignment is None:
        raise AssignmentValidationError(
            "An assignment is required."
        )

    _validate_actor(
        actor=actor,
        organization=assignment.organization,
    )

    if not assignment.is_active:
        return assignment

    now = timezone.now()

    assignment.is_active = False
    assignment.status = ResourceAssignment.STATUS_CANCELLED
    assignment.revoked_at = now
    assignment.revoked_by = actor
    assignment.revoke_reason = reason or ""

    assignment.save()

    ResourceAccess.objects.filter(
        assignment=assignment,
        is_active=True,
    ).update(
        is_active=False,
        revoked_at=now,
    )

    return assignment


# ============================================================
# START ASSIGNMENT
# ============================================================


@transaction.atomic
def start_assignment(
    *,
    assignment,
):
    """
    Mark an assignment as started.
    """

    if assignment is None:
        raise AssignmentValidationError(
            "An assignment is required."
        )

    if not assignment.is_active:
        raise AssignmentValidationError(
            "Cannot start an inactive assignment."
        )

    if assignment.status != ResourceAssignment.STATUS_ASSIGNED:
        return assignment

    assignment.status = ResourceAssignment.STATUS_STARTED

    assignment.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return assignment


# ============================================================
# COMPLETE ASSIGNMENT
# ============================================================


@transaction.atomic
def complete_assignment(
    *,
    assignment,
):
    """
    Mark an assignment as completed.

    Completion does not delete assignment history.
    """

    if assignment is None:
        raise AssignmentValidationError(
            "An assignment is required."
        )

    if not assignment.is_active:
        raise AssignmentValidationError(
            "Cannot complete an inactive assignment."
        )

    assignment.status = ResourceAssignment.STATUS_COMPLETED
    assignment.completed_at = timezone.now()

    assignment.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    return assignment


# ============================================================
# EXPIRE ASSIGNMENT
# ============================================================


@transaction.atomic
def expire_assignment(
    *,
    assignment,
):
    """
    Expire an assignment and disable its active access.
    """

    if assignment is None:
        raise AssignmentValidationError(
            "An assignment is required."
        )

    if not assignment.is_active:
        return assignment

    now = timezone.now()

    assignment.is_active = False
    assignment.status = ResourceAssignment.STATUS_EXPIRED

    if assignment.revoked_at is None:
        assignment.revoked_at = now

    assignment.save(
        update_fields=[
            "is_active",
            "status",
            "revoked_at",
            "updated_at",
        ]
    )

    ResourceAccess.objects.filter(
        assignment=assignment,
        is_active=True,
    ).update(
        is_active=False,
        revoked_at=assignment.revoked_at,
    )

    return assignment