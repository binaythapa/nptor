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


class AssignmentError(Exception):
    pass
class InvalidAssignmentError(AssignmentError):
    pass
class StudentNotInOrganizationError(AssignmentError):
    pass
class DuplicateActiveAssignmentError(AssignmentError):
    pass
class ResourceNotAvailableError(AssignmentError):
    pass
class UnauthorizedAssignmentError(AssignmentError):
    pass
class AssignmentPermissionError(AssignmentError):
    pass
AssignmentValidationError = InvalidAssignmentError
AssignmentDuplicateError = DuplicateActiveAssignmentError
AssignmentNotFoundError = ResourceNotAvailableError


@dataclass
class AssignmentResult:
    assignment: ResourceAssignment
    access: ResourceAccess
    created: bool


def _validate_actor(*, actor, organization):
    if actor is None or not actor.is_authenticated:
        raise AssignmentPermissionError("Authentication is required.")
    membership = OrganizationMember.objects.filter(
        user=actor, organization=organization, is_active=True,
    ).first()
    if not membership:
        raise AssignmentPermissionError("You are not an active member of this organization.")
    if not membership.can_manage_students:
        raise UnauthorizedAssignmentError("You do not have permission to manage student assignments.")
    return membership


def _validate_student(*, student, organization):
    membership = OrganizationMember.objects.filter(
        user=student, organization=organization,
        role=OrganizationMember.ROLE_STUDENT, is_active=True,
    ).first()
    if not membership:
        raise StudentNotInOrganizationError("The selected user is not an active student of this organization.")
    return membership


def _validate_dates(*, starts_at: Optional[datetime] = None, due_at: Optional[datetime] = None, expires_at: Optional[datetime] = None):
    if starts_at and due_at and due_at <= starts_at:
        raise InvalidAssignmentError("The due date must be later than the start date.")
    if starts_at and expires_at and expires_at <= starts_at:
        raise InvalidAssignmentError("The expiration date must be later than the start date.")
    if due_at and expires_at and expires_at < due_at:
        raise InvalidAssignmentError("The expiration date cannot be earlier than the due date.")


def _resource_filter(*, resource_type, resource):
    if resource_type == ResourceAssignment.RESOURCE_COURSE:
        return {"course": resource}
    if resource_type == ResourceAssignment.RESOURCE_TRACK:
        return {"track": resource}
    if resource_type == ResourceAssignment.RESOURCE_EXAM:
        return {"exam": resource}
    raise InvalidAssignmentError("Unsupported resource type.")


def _get_resource(*, resource_type, resource_id, organization):
    if not resource_id:
        raise InvalidAssignmentError("A resource ID is required.")

    if resource_type == ResourceAssignment.RESOURCE_COURSE:
        resource = Course.objects.filter(pk=resource_id).first()
        if not resource:
            raise ResourceNotAvailableError("Course not found.")
        if resource.organization_id is not None and resource.organization_id != organization.id:
            raise ResourceNotAvailableError("This course is not available to this organization.")
        return resource

    if resource_type == ResourceAssignment.RESOURCE_TRACK:
        resource = ExamTrack.objects.filter(pk=resource_id, organization=organization).first()
        if not resource:
            raise ResourceNotAvailableError("Exam track not found or is not available to this organization.")
        return resource

    # Exams remain reusable content. They are intentionally not a standalone
    # student-assignment resource; assign the Course or Track containing them.
    if resource_type == ResourceAssignment.RESOURCE_EXAM:
        raise InvalidAssignmentError("Exams cannot be assigned directly. Assign the Course or Track containing the Exam.")

    raise InvalidAssignmentError("Unsupported resource type.")


def _find_active_assignment(*, student, organization, resource_type, resource):
    filters = {
        "student": student, "organization": organization,
        "resource_type": resource_type, "is_active": True,
    }
    filters.update(_resource_filter(resource_type=resource_type, resource=resource))
    return ResourceAssignment.objects.filter(**filters).first()


def _find_latest_assignment(*, student, organization, resource_type, resource):
    filters = {
        "student": student, "organization": organization,
        "resource_type": resource_type,
    }
    filters.update(_resource_filter(resource_type=resource_type, resource=resource))
    return ResourceAssignment.objects.filter(**filters).order_by("-assigned_at").first()


def _get_or_create_resource_access(*, student, organization, resource_type, resource, assignment, expires_at=None):
    filters = {
        "user": student, "organization": organization,
        "resource_type": resource_type,
        "source": ResourceAccess.SOURCE_ORGANIZATION,
    }
    filters.update(_resource_filter(resource_type=resource_type, resource=resource))
    defaults = {"assignment": assignment, "is_active": True, "expires_at": expires_at}
    access, created = ResourceAccess.objects.get_or_create(**filters, defaults=defaults)
    if created:
        return access
    update_fields = []
    if access.assignment_id != assignment.id:
        access.assignment = assignment
        update_fields.append("assignment")
    if not access.is_active:
        access.is_active = True
        access.revoked_at = None
        update_fields.extend(["is_active", "revoked_at"])
    if access.expires_at != expires_at:
        access.expires_at = expires_at
        update_fields.append("expires_at")
    if update_fields:
        access.save(update_fields=update_fields)
    return access


@transaction.atomic
def assign_resource(*, student, organization, resource_type, resource_id, actor, starts_at=None, due_at=None, expires_at=None, notes="", allow_reactivate=False):
    """Assign a Course or Track to an organization student."""
    if organization is None:
        raise InvalidAssignmentError("An organization is required.")
    if not organization.is_active:
        raise InvalidAssignmentError("Cannot create assignments for an inactive organization.")

    _validate_actor(actor=actor, organization=organization)
    _validate_student(student=student, organization=organization)

    valid_types = {
        ResourceAssignment.RESOURCE_COURSE,
        ResourceAssignment.RESOURCE_TRACK,
    }
    if resource_type not in valid_types:
        raise InvalidAssignmentError("Only Courses and Tracks can be assigned to students.")

    _validate_dates(starts_at=starts_at, due_at=due_at, expires_at=expires_at)
    resource = _get_resource(resource_type=resource_type, resource_id=resource_id, organization=organization)

    active_assignment = _find_active_assignment(
        student=student, organization=organization,
        resource_type=resource_type, resource=resource,
    )
    if active_assignment:
        raise DuplicateActiveAssignmentError("This resource is already assigned to this student.")

    historical_assignment = _find_latest_assignment(
        student=student, organization=organization,
        resource_type=resource_type, resource=resource,
    )

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
    else:
        assignment = ResourceAssignment(
            student=student, organization=organization, assigned_by=actor,
            resource_type=resource_type, status=ResourceAssignment.STATUS_ASSIGNED,
            is_active=True, starts_at=starts_at, due_at=due_at,
            expires_at=expires_at, notes=notes or "",
        )
        if resource_type == ResourceAssignment.RESOURCE_COURSE:
            assignment.course = resource
        else:
            assignment.track = resource
        assignment.save()

    access = _get_or_create_resource_access(
        student=student, organization=organization,
        resource_type=resource_type, resource=resource,
        assignment=assignment, expires_at=expires_at,
    )
    return AssignmentResult(
        assignment=assignment,
        access=access,
        created=not bool(historical_assignment and allow_reactivate),
    )


@transaction.atomic
def revoke_assignment(*, assignment, actor, reason=""):
    if assignment is None:
        raise InvalidAssignmentError("An assignment is required.")
    _validate_actor(actor=actor, organization=assignment.organization)
    if not assignment.is_active:
        return assignment
    now = timezone.now()
    assignment.is_active = False
    assignment.status = ResourceAssignment.STATUS_REVOKED
    assignment.revoked_at = now
    assignment.revoked_by = actor
    assignment.revoke_reason = reason or ""
    assignment.save()
    ResourceAccess.objects.filter(assignment=assignment, is_active=True).update(is_active=False, revoked_at=now)
    return assignment
