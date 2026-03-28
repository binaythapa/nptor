from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember, OrganizationGroup


# ===============================
# LIST STUDENTS
# ===============================
@org_admin_required
def org_students(request, slug):

    org = request.organization

    members = (
        OrganizationMember.objects
        .filter(organization=org)
        .select_related("user", "group")
        .order_by("role", "user__username")
    )

    # ✅ ALL groups (no group_type)
    groups = OrganizationGroup.objects.filter(
        organization=org,
        is_active=True
    )

    return render(
        request,
        "organizations/admin/students/list.html",
        {
            "members": members,
            "org": org,
            "groups": groups,
        }
    )


# ===============================
# ADD STUDENT
# ===============================
@org_admin_required
def org_student_add(request, slug):

    org = request.organization

    # ✅ FIXED: removed group_type
    groups = OrganizationGroup.objects.filter(
        organization=org,
        is_active=True
    )

    if request.method == "POST":

        email = request.POST.get("email")
        role = request.POST.get("role", "student")
        group_id = request.POST.get("group")

        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "User with this email does not exist.")
            return redirect("organizations_admin:students", slug=slug)

        group = None
        if group_id and group_id.isdigit():
            group = OrganizationGroup.objects.filter(
                id=group_id,
                organization=org
            ).first()

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=org,
            defaults={
                "role": role,
                "group": group,
                "is_active": True,
            }
        )

        messages.success(
            request,
            f"{user.email} added to organization."
        )

        return redirect("organizations_admin:students", slug=slug)

    return render(
        request,
        "organizations/admin/students/add.html",
        {
            "org": org,
            "groups": groups,
        }
    )


# ===============================
# UPDATE ROLE + GROUP
# ===============================
@org_admin_required
def org_student_update_role(request, slug, member_id):

    org = request.organization

    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=org
    )

    if request.method == "POST":

        new_role = request.POST.get("role")
        group_id = request.POST.get("group")

        # ✅ UPDATE ROLE
        if new_role in ["student", "staff"]:
            member.role = new_role

        # ✅ UPDATE GROUP (no group_type)
        if group_id and group_id.isdigit():
            group = OrganizationGroup.objects.filter(
                id=group_id,
                organization=org
            ).first()
            member.group = group
        else:
            member.group = None

        member.save()

        messages.success(request, "Updated successfully.")

    return redirect("organizations_admin:students", slug=slug)


# ===============================
# REMOVE STUDENT
# ===============================
@org_admin_required
def org_student_remove(request, slug, member_id):

    org = request.organization

    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=org
    )

    if member.role == "org_admin":
        messages.error(request, "Cannot remove organization admin.")
        return redirect("organizations_admin:students", slug=slug)

    member.delete()

    messages.success(
        request,
        "Member removed from organization."
    )

    return redirect("organizations_admin:students", slug=slug)