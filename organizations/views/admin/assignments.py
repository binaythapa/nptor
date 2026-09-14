# organizations/views/admin/assignments.py

"""Organization assignment administration views."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

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
from quiz.models import ExamTrack


def _assignment_form_context(organization):
    """Return only resources that can be assigned to organization students."""
    students = (
        OrganizationMember.objects
        .filter(
            organization=organization,
            role=OrganizationMember.ROLE_STUDENT,
            is_active=True,
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__username")
    )

    # Organization-owned courses are internal resources and do not require
    # an organization subscription. Platform courses remain assignable when
    # they are explicitly attached to the organization.
    organization_courses = Course.objects.filter(organization=organization)
    attached_platform_courses = Course.objects.filter(
        organization_subscriptions__organization=organization,
        organization_subscriptions__is_active=True,
    )
    courses = (organization_courses | attached_platform_courses).distinct().order_by("title")

    tracks = ExamTrack.objects.filter(organization=organization).order_by("title")

    return {
        "students": students,
        "courses": courses,
        "tracks": tracks,
        "org": organization,
    }


def _parse_datetime(value):
    if not value:
        return None
    from datetime import datetime
    from django.utils import timezone
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _filter_assignments(assignments, query):
    """Filter organization assignments by student, resource, type, or status."""
    if not query:
        return assignments

    return assignments.filter(
        Q(student__first_name__icontains=query)
        | Q(student__last_name__icontains=query)
        | Q(student__username__icontains=query)
        | Q(student__email__icontains=query)
        | Q(course__title__icontains=query)
        | Q(track__title__icontains=query)
        | Q(exam__title__icontains=query)
        | Q(resource_type__icontains=query)
        | Q(status__icontains=query)
    )


@org_teacher_required
def org_assignments(request, slug):
    organization = request.organization
    search_query = (request.GET.get("q") or "").strip()
    assignments = (
        ResourceAssignment.objects
        .filter(organization=organization)
        .select_related("student", "assigned_by", "revoked_by", "course", "track", "exam")
        .order_by("-assigned_at")
    )
    assignments = _filter_assignments(assignments, search_query)

    return render(
        request,
        "organizations/admin/assignments/list.html",
        {
            "assignments": assignments,
            "org": organization,
            "search_query": search_query,
        },
    )


@org_teacher_required
def org_assignment_create(request, slug):
    organization = request.organization
    context = _assignment_form_context(organization)

    if request.method != "POST":
        return render(request, "organizations/admin/assignments/create.html", context)

    student_id = request.POST.get("student_id")
    resource_type = request.POST.get("resource_type")
    if not student_id:
        messages.error(request, "Please select a student.")
        return render(request, "organizations/admin/assignments/create.html", context)
    if resource_type not in {
        ResourceAssignment.RESOURCE_COURSE,
        ResourceAssignment.RESOURCE_TRACK,
    }:
        messages.error(request, "Please select a Course or Track.")
        return render(request, "organizations/admin/assignments/create.html", context)

    student_membership = get_object_or_404(
        OrganizationMember,
        id=student_id,
        organization=organization,
        role=OrganizationMember.ROLE_STUDENT,
        is_active=True,
    )

    resource_id = request.POST.get("course_id" if resource_type == ResourceAssignment.RESOURCE_COURSE else "track_id")
    if not resource_id:
        messages.error(request, "Please select a resource.")
        return render(request, "organizations/admin/assignments/create.html", context)

    try:
        result = assign_resource(
            actor=request.user,
            organization=organization,
            student=student_membership.user,
            resource_type=resource_type,
            resource_id=resource_id,
            starts_at=_parse_datetime(request.POST.get("starts_at")),
            due_at=_parse_datetime(request.POST.get("due_at")),
            expires_at=_parse_datetime(request.POST.get("expires_at")),
            notes=(request.POST.get("notes") or "").strip(),
        )
    except DuplicateActiveAssignmentError as exc:
        messages.warning(request, str(exc))
        return redirect("organizations_admin:assignments", slug=slug)
    except (
        StudentNotInOrganizationError,
        UnauthorizedAssignmentError,
        ResourceNotAvailableError,
        InvalidAssignmentError,
        AssignmentError,
    ) as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:assignments", slug=slug)

    resource_name = result.assignment.resource_name or "Resource"
    messages.success(
        request,
        f"{resource_name} was successfully assigned to {student_membership.user.email}." if result.created
        else f"{resource_name} assignment for {student_membership.user.email} was reactivated.",
    )
    return redirect("organizations_admin:assignments", slug=slug)


@org_teacher_required
def org_assignment_remove(request, slug, assignment_id):
    assignment = get_object_or_404(
        ResourceAssignment,
        id=assignment_id,
        organization=request.organization,
    )
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("organizations_admin:assignments", slug=slug)
    try:
        revoke_assignment(
            assignment=assignment,
            actor=request.user,
            reason=(request.POST.get("reason") or "Assignment revoked by organization staff.").strip(),
        )
    except (UnauthorizedAssignmentError, InvalidAssignmentError, AssignmentError) as exc:
        messages.error(request, str(exc))
        return redirect("organizations_admin:assignments", slug=slug)
    messages.success(request, "Assignment revoked successfully.")
    return redirect("organizations_admin:assignments", slug=slug)
