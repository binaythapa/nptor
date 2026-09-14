from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required, org_teacher_required
from organizations.models import OrganizationStudent
from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole


User = get_user_model()


@org_teacher_required
def org_students(request, slug):
    org = request.organization

    members = list(
        OrganizationMember.objects
        .filter(organization=org)
        .select_related("user")
        .order_by("role", "user__username")
    )

    student_profiles = OrganizationStudent.objects.filter(
        organization=org,
        user_id__in=[member.user_id for member in members],
    ).values_list("user_id", "id")
    profile_ids = dict(student_profiles)

    for member in members:
        member.student_profile_id = profile_ids.get(member.user_id)

    return render(
        request,
        "organizations/admin/students/list.html",
        {"members": members, "org": org},
    )


@org_admin_required
def org_student_detail(request, slug, student_id):
    """Render an organization-admin-only view of one student's profile."""
    org = request.organization

    student = get_object_or_404(
        OrganizationStudent.objects.select_related("user"),
        id=student_id,
        organization=org,
        status=OrganizationStudent.STATUS_ACTIVE,
    )

    get_object_or_404(
        OrganizationMember,
        organization=org,
        user=student.user,
        role=OrganizationRole.STUDENT,
        is_active=True,
    )

    return render(
        request,
        "organizations/admin/students/detail.html",
        {"org": org, "student": student},
    )


@org_teacher_required
def org_student_add(request, slug):
    org = request.organization

    if request.method == "GET":
        return render(
            request,
            "organizations/admin/students/add.html",
            {"org": org},
        )

    email = (request.POST.get("email") or "").strip().lower()
    role = request.POST.get("role", OrganizationRole.STUDENT)

    # Staff/teachers may add students only. Owners/admins may also add staff.
    if request.organization_member.role == OrganizationRole.STAFF:
        if role != OrganizationRole.STUDENT:
            messages.error(request, "Staff / Teacher members can add students only.")
            return redirect("organizations_admin:students", slug=slug)
    elif role not in {OrganizationRole.STUDENT, OrganizationRole.STAFF}:
        messages.error(request, "Invalid organization role.")
        return redirect("organizations_admin:students", slug=slug)

    user = User.objects.filter(email__iexact=email).first()

    if not user:
        messages.error(request, "User with this email does not exist.")
        return redirect("organizations_admin:students", slug=slug)

    member, created = OrganizationMember.objects.get_or_create(
        user=user,
        organization=org,
        defaults={
            "role": role,
            "is_active": True,
        },
    )

    # Staff/teachers cannot change an existing staff membership into a student.
    if not created and request.organization_member.role == OrganizationRole.STAFF and member.role != OrganizationRole.STUDENT:
        messages.error(request, "Staff / Teacher members cannot change another staff member's role.")
        return redirect("organizations_admin:students", slug=slug)

    if not created:
        member.role = role
        member.is_active = True
        member.save(update_fields=["role", "is_active"])

    # Every active student membership gets an active organization-scoped profile.
    # Re-adding a previously removed student also reactivates the existing profile.
    if member.role == OrganizationRole.STUDENT and member.is_active:
        student, created = OrganizationStudent.objects.get_or_create(
            organization=org,
            user=user,
            defaults={
                "status": OrganizationStudent.STATUS_ACTIVE,
                "joined_date": timezone.localdate(),
            },
        )
        if not created and student.status != OrganizationStudent.STATUS_ACTIVE:
            student.status = OrganizationStudent.STATUS_ACTIVE
            if not student.joined_date:
                student.joined_date = timezone.localdate()
                student.save(update_fields=["status", "joined_date", "updated_at"])
            else:
                student.save(update_fields=["status", "updated_at"])

    messages.success(request, f"{user.email} added to organization.")
    return redirect("organizations_admin:students", slug=slug)


@org_admin_required
@require_POST
def org_student_update_role(request, slug, member_id):
    org = request.organization

    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=org,
    )

    new_role = request.POST.get("role")

    if new_role not in {OrganizationRole.STUDENT, OrganizationRole.STAFF}:
        messages.error(request, "Invalid organization role.")
        return redirect("organizations_admin:students", slug=slug)

    # Owners/admins must not be demoted through the student-management endpoint.
    if member.role in OrganizationRole.administrative_roles():
        messages.error(request, "Organization administrators must be managed separately.")
        return redirect("organizations_admin:students", slug=slug)

    member.role = new_role
    member.save(update_fields=["role"])

    if new_role == OrganizationRole.STUDENT and member.is_active:
        student, created = OrganizationStudent.objects.get_or_create(
            organization=org,
            user=member.user,
            defaults={
                "status": OrganizationStudent.STATUS_ACTIVE,
                "joined_date": timezone.localdate(),
            },
        )
        if not created and student.status != OrganizationStudent.STATUS_ACTIVE:
            student.status = OrganizationStudent.STATUS_ACTIVE
            student.save(update_fields=["status", "updated_at"])
    elif new_role == OrganizationRole.STAFF:
        # Do not create a profile for a staff member. If this member used to
        # be a student, preserve that record as history but deactivate it.
        OrganizationStudent.objects.filter(
            organization=org,
            user=member.user,
        ).update(
            status=OrganizationStudent.STATUS_INACTIVE,
            updated_at=timezone.now(),
        )

    messages.success(request, "Role updated successfully.")
    return redirect("organizations_admin:students", slug=slug)


@org_teacher_required
@require_POST
def org_student_remove(request, slug, member_id):
    org = request.organization

    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=org,
    )

    if member.role in OrganizationRole.administrative_roles():
        messages.error(request, "Cannot remove an organization administrator here.")
        return redirect("organizations_admin:students", slug=slug)

    if request.organization_member.role == OrganizationRole.STAFF and member.role != OrganizationRole.STUDENT:
        messages.error(request, "Staff / Teacher members can remove students only.")
        return redirect("organizations_admin:students", slug=slug)

    # Removing membership must also revoke organization-granted access.
    # Keep ResourceAssignment rows as historical audit records.
    now = timezone.now()

    ResourceAssignment.objects.filter(
        student=member.user,
        organization=org,
        is_active=True,
    ).update(
        is_active=False,
        status=ResourceAssignment.STATUS_REVOKED,
        revoked_at=now,
        revoked_by=request.user,
        revoke_reason="Student removed from organization.",
    )

    ResourceAccess.objects.filter(
        user=member.user,
        organization=org,
        source=ResourceAccess.SOURCE_ORGANIZATION,
        is_active=True,
    ).update(
        is_active=False,
        revoked_at=now,
    )

    # Preserve the organization-scoped profile as historical data while
    # deactivating it. This keeps IDs/admission history available if the
    # student is later re-added to the organization.
    if member.role == OrganizationRole.STUDENT:
        OrganizationStudent.objects.filter(
            organization=org,
            user=member.user,
        ).update(
            status=OrganizationStudent.STATUS_INACTIVE,
            updated_at=now,
        )

    member.delete()
    messages.success(request, "Student removed from organization.")
    return redirect("organizations_admin:students", slug=slug)
