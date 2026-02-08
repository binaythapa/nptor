from django.shortcuts import render
from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User

from organizations.permissions import org_admin_required
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization


@org_admin_required
def org_students(request):
    members = (
        OrganizationMember.objects
        .filter(organization=request.active_org)
        .select_related("user")
        .order_by("role", "user__username")
    )

    return render(
        request,
        "organizations/admin/students/list.html",
        {"members": members}
    )


@org_admin_required
def org_student_add(request):
    if request.method == "POST":
        email = request.POST.get("email")
        role = request.POST.get("role", "student")

        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User with this email does not exist.")
            return redirect("organizations_admin:students")

        OrganizationMember.objects.get_or_create(
            user=user,
            organization=request.active_org,
            defaults={
                "role": role,
                "is_active": True,
            }
        )

        messages.success(request, f"{user.email} added to organization.")
        return redirect("organizations_admin:students")

    return render(
        request,
        "organizations/admin/students/add.html"
    )

@org_admin_required
def org_student_update_role(request, member_id):
    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=request.active_org
    )

    if request.method == "POST":
        new_role = request.POST.get("role")
        if new_role in ["student", "staff"]:
            member.role = new_role
            member.save()
            messages.success(request, "Role updated successfully.")

    return redirect("organizations_admin:students")

@org_admin_required
def org_student_remove(request, member_id):
    member = get_object_or_404(
        OrganizationMember,
        id=member_id,
        organization=request.active_org
    )

    if member.role == "org_admin":
        messages.error(request, "Cannot remove organization admin.")
        return redirect("organizations_admin:students")

    member.delete()
    messages.success(request, "Student removed from organization.")
    return redirect("organizations_admin:students")

