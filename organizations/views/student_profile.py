from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from organizations.forms.student import OrganizationStudentProfileForm
from organizations.models import OrganizationStudent
from organizations.permissions import org_admin_required, org_student_required
from organizations.services.students import get_organization_student, get_student_for_teacher, update_student_profile


@org_student_required
def organization_student_profile(request, slug):
    student = get_organization_student(request.user, request.organization)
    return render(request, "organizations/student/profile.html", {"organization": request.organization, "student": student, "membership": request.organization_member})


@org_student_required
def organization_student_profile_edit(request, slug):
    student = get_organization_student(request.user, request.organization)
    if request.method == "POST":
        form = OrganizationStudentProfileForm(request.POST, instance=student)
        if form.is_valid():
            update_student_profile(actor=request.user, organization=request.organization, student=student, data=form.cleaned_data)
            messages.success(request, "Your organization profile has been updated.")
            return redirect("organizations_public:student_profile", slug=slug)
    else:
        form = OrganizationStudentProfileForm(instance=student)
    return render(request, "organizations/student/profile_edit.html", {"organization": request.organization, "student": student, "form": form})


@org_admin_required
def organization_student_profile_admin(request, slug, student_id):
    student = get_object_or_404(OrganizationStudent.objects.select_related("user", "organization"), id=student_id, organization=request.organization)
    return render(request, "organizations/student/profile.html", {"organization": request.organization, "student": student, "admin_view": True})


@org_admin_required
def organization_student_profile_admin_edit(request, slug, student_id):
    student = get_object_or_404(OrganizationStudent.objects.select_related("user", "organization"), id=student_id, organization=request.organization)
    if request.method == "POST":
        form = OrganizationStudentProfileForm(request.POST, instance=student)
        if form.is_valid():
            update_student_profile(actor=request.user, organization=request.organization, student=student, data=form.cleaned_data)
            messages.success(request, "Student profile updated.")
            return redirect("organizations_public:student_profile_admin", slug=slug, student_id=student.id)
    else:
        form = OrganizationStudentProfileForm(instance=student)
    return render(request, "organizations/student/profile_edit.html", {"organization": request.organization, "student": student, "form": form, "admin_view": True})
