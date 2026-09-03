from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole


User = get_user_model()


@org_admin_required
def org_students(request, slug):
    org = request.organization

    members = (
        OrganizationMember.objects
        .filter(organization=org)
        .select_related("user")
        .order_by("role", "user__username")
    )

    return render(
        request,
        "organizations/admin/students/list.html",
        {"members": members, "org": org},
    )


@org_admin_required
@require_POST
def org_student_add(request, slug):
    org = request.organization
    email = (request.POST.get("email") or "").strip().lower()
    role = request.POST.get("role", OrganizationRole.STUDENT)

    # Never allow this endpoint to create an owner/admin membership.
    if role not in {OrganizationRole.STUDENT, OrganizationRole.STAFF}:
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

    if not created:
        member.role = role
        member.is_active = True
        member.save(update_fields=["role", "is_active"])

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
    messages.success(request, "Role updated successfully.")
    return redirect("organizations_admin:students", slug=slug)


@org_admin_required
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

    member.delete()
    messages.success(request, "Student removed from organization.")
    return redirect("organizations_admin:students", slug=slug)
