# organizations/views/admin/assignments.py

"""
Organization assignment administration views.

The views in this module are intentionally thin.

Architecture:

    Request
        ↓
    Organization permission layer
        ↓
    Assignment service
        ↓
    ResourceAssignment + ResourceAccess

Business rules must remain in:

    organizations.services.assignments
"""

from django.contrib import messages
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from organizations.permissions import org_teacher_required
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.services.assignments import (
    assign_resource,
    revoke_assignment,
    DuplicateActiveAssignmentError,
    AssignmentError,
    ResourceNotAvailableError,
    StudentNotInOrganizationError,
    UnauthorizedAssignmentError,
    InvalidAssignmentError,
)

from courses.models import Course
from quiz.models import Exam, ExamTrack


# ============================================================
# COMMON CONTEXT
# ============================================================


def _assignment_form_context(organization):
    """
    Build the data required by the assignment creation form.

    This function only prepares querysets for presentation.
    Assignment business logic belongs to the service layer.
    """

    students = (
        OrganizationMember.objects
        .filter(
            organization=organization,
            role=OrganizationMember.ROLE_STUDENT,
            is_active=True,
        )
        .select_related("user")
        .order_by(
            "user__first_name",
            "user__last_name",
            "user__username",
        )
    )

    courses = (
        Course.objects
        .filter(
            organization_subscriptions__organization=organization,
            organization_subscriptions__is_active=True,
        )
        .distinct()
        .order_by("title")
    )

    tracks = (
        ExamTrack.objects
        .filter(
            organization=organization,
        )
        .order_by("title")
    )

    exams = (
        Exam.objects
        .filter(
            organization=organization,
        )
        .order_by("title")
    )

    return {
        "students": students,
        "courses": courses,
        "tracks": tracks,
        "exams": exams,
        "org": organization,
    }


# ============================================================
# DATETIME HELPER
# ============================================================


def _parse_datetime(value):
    """
    Convert an HTML datetime-local value into an aware
    Django datetime.

    Browser format:

        YYYY-MM-DDTHH:MM

    Empty or invalid values return None.
    """

    if not value:
        return None

    from datetime import datetime

    from django.utils import timezone

    try:
        parsed = datetime.fromisoformat(value)

    except (TypeError, ValueError):
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)

    return parsed


# ============================================================
# LIST ASSIGNMENTS
# ============================================================


@org_teacher_required
def org_assignments(request, slug):
    """
    Display assignments belonging to the active organization.

    Organization owners, admins, and staff/teachers may view
    assignments according to the organization permission layer.
    """

    organization = request.organization

    assignments = (
        ResourceAssignment.objects
        .filter(
            organization=organization,
        )
        .select_related(
            "student",
            "assigned_by",
            "revoked_by",
            "course",
            "track",
            "exam",
            "resource_access",
        )
        .order_by("-assigned_at")
    )

    return render(
        request,
        "organizations/admin/assignments/list.html",
        {
            "assignments": assignments,
            "org": organization,
        },
    )


# ============================================================
# CREATE ASSIGNMENT
# ============================================================


@org_teacher_required
def org_assignment_create(request, slug):
    """
    Create a resource assignment for an organization student.

    The view performs HTTP/form handling only.

    Actual assignment creation is handled by:

        organizations.services.assignments.assign_resource()
    """

    organization = request.organization

    context = _assignment_form_context(
        organization,
    )

    # ========================================================
    # GET
    # ========================================================

    if request.method != "POST":

        return render(
            request,
            "organizations/admin/assignments/create.html",
            context,
        )

    # ========================================================
    # BASIC INPUT
    # ========================================================

    student_id = request.POST.get(
        "student_id",
    )

    resource_type = request.POST.get(
        "resource_type",
    )

    if not student_id:

        messages.error(
            request,
            "Please select a student.",
        )

        return render(
            request,
            "organizations/admin/assignments/create.html",
            context,
        )

    if not resource_type:

        messages.error(
            request,
            "Please select a resource type.",
        )

        return render(
            request,
            "organizations/admin/assignments/create.html",
            context,
        )

    # ========================================================
    # STUDENT
    # ========================================================

    student_membership = get_object_or_404(
        OrganizationMember,
        id=student_id,
        organization=organization,
        role=OrganizationMember.ROLE_STUDENT,
        is_active=True,
    )

    student = student_membership.user

    # ========================================================
    # RESOURCE ID
    # ========================================================

    if resource_type == ResourceAssignment.RESOURCE_COURSE:

        resource_id = request.POST.get(
            "course_id",
        )

    elif resource_type == ResourceAssignment.RESOURCE_TRACK:

        resource_id = request.POST.get(
            "track_id",
        )

    elif resource_type == ResourceAssignment.RESOURCE_EXAM:

        resource_id = request.POST.get(
            "exam_id",
        )

    else:

        messages.error(
            request,
            "Invalid resource type.",
        )

        return render(
            request,
            "organizations/admin/assignments/create.html",
            context,
        )

    if not resource_id:

        messages.error(
            request,
            "Please select a resource.",
        )

        return render(
            request,
            "organizations/admin/assignments/create.html",
            context,
        )

    # ========================================================
    # TIMELINE
    # ========================================================

    starts_at = _parse_datetime(
        request.POST.get(
            "starts_at",
        )
    )

    due_at = _parse_datetime(
        request.POST.get(
            "due_at",
        )
    )

    expires_at = _parse_datetime(
        request.POST.get(
            "expires_at",
        )
    )

    notes = (
        request.POST.get(
            "notes",
        )
        or ""
    ).strip()

    # ========================================================
    # ASSIGN RESOURCE
    # ========================================================

    try:

        result = assign_resource(
            actor=request.user,
            organization=organization,
            student=student,
            resource_type=resource_type,
            resource_id=resource_id,
            starts_at=starts_at,
            due_at=due_at,
            expires_at=expires_at,
            notes=notes,
        )

    except DuplicateActiveAssignmentError as exc:

        messages.warning(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:assignments",
            slug=slug,
        )

    except (
        StudentNotInOrganizationError,
        UnauthorizedAssignmentError,
        ResourceNotAvailableError,
        InvalidAssignmentError,
        AssignmentError,
    ) as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:assignments",
            slug=slug,
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    assignment = result.assignment

    resource_name = (
        assignment.resource_name
        or "Resource"
    )

    if result.created:

        messages.success(
            request,
            (
                f"{resource_name} was successfully assigned "
                f"to {student.email}."
            ),
        )

    else:

        messages.success(
            request,
            (
                f"{resource_name} assignment for "
                f"{student.email} was reactivated."
            ),
        )

    return redirect(
        "organizations_admin:assignments",
        slug=slug,
    )


# ============================================================
# REVOKE ASSIGNMENT
# ============================================================


@org_teacher_required
def org_assignment_remove(
    request,
    slug,
    assignment_id,
):
    """
    Revoke an assignment.

    IMPORTANT:

    We do not delete the assignment.

    The historical record remains available for:

        - audit
        - reporting
        - progress history
        - organization reporting
        - compliance
    """

    organization = request.organization

    assignment = get_object_or_404(
        ResourceAssignment,
        id=assignment_id,
        organization=organization,
    )

    # ========================================================
    # POST ONLY
    # ========================================================

    if request.method != "POST":

        messages.error(
            request,
            "Invalid request method.",
        )

        return redirect(
            "organizations_admin:assignments",
            slug=slug,
        )

    # ========================================================
    # REASON
    # ========================================================

    reason = (
        request.POST.get(
            "reason",
        )
        or "Assignment revoked by organization staff."
    ).strip()

    # ========================================================
    # REVOKE THROUGH SERVICE
    # ========================================================

    try:

        revoke_assignment(
            assignment=assignment,
            actor=request.user,
            reason=reason,
        )

    except (
        UnauthorizedAssignmentError,
        InvalidAssignmentError,
        AssignmentError,
    ) as exc:

        messages.error(
            request,
            str(exc),
        )

        return redirect(
            "organizations_admin:assignments",
            slug=slug,
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    messages.success(
        request,
        "Assignment revoked successfully.",
    )

    return redirect(
        "organizations_admin:assignments",
        slug=slug,
    )