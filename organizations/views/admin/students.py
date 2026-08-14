from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember


# ===============================
# LIST STUDENTS
# ===============================
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
        {
            "members": members,
            "org": org,
        }
    )


# ===============================
# ADD STUDENT
# ===============================
@org_admin_required
def org_student_add(request, slug):

    org = request.organization

    if request.method == "POST":

        email = request.POST.get("email")
        role = request.POST.get("role", "student")

        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "User with this email does not exist.")
            return redirect(
                "organizations_admin:students",
                slug=slug
            )

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=org,
            defaults={
                "role": role,
                "is_active": True,
            }
        )

        messages.success(
            request,
            f"{user.email} added to organization."
        )

        return redirect(
            "organizations_admin:students",
            slug=slug
        )

    return render(
        request,
        "organizations/admin/students/add.html",
        {
            "org": org
        }
    )


# ===============================
# UPDATE ROLE
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

        if new_role in ["student", "staff"]:
            member.role = new_role
            member.save()

            messages.success(
                request,
                "Role updated successfully."
            )

    return redirect(
        "organizations_admin:students",
        slug=slug
    )


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
        messages.error(
            request,
            "Cannot remove organization admin."
        )

        return redirect(
            "organizations_admin:students",
            slug=slug
        )

    member.delete()

    messages.success(
        request,
        "Student removed from organization."
    )

    return redirect(
        "organizations_admin:students",
        slug=slug
    )