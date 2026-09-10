from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from organizations.models import AcademicYear, ClassSection, ClassTeacher, OrganizationClass, OrganizationStudent
from organizations.permissions import org_admin_required, org_teacher_required
from organizations.services.enrollment import assign_teacher_to_section, enroll_student, transfer_student


@org_teacher_required
def academic_dashboard(request, slug):
    org = request.organization
    years = org.academic_years.all()
    sections = org.class_sections.select_related("academic_year", "class_group").all()
    if request.organization_member.role == "staff":
        sections = sections.filter(teacher_assignments__teacher=request.user, teacher_assignments__is_active=True).distinct()
    return render(request, "organizations/admin/academic/dashboard.html", {"org": org, "years": years, "sections": sections})


@org_admin_required
def academic_year_create(request, slug):
    if request.method == "POST":
        year = AcademicYear(organization=request.organization, name=request.POST.get("name", "").strip(), start_date=request.POST.get("start_date"), end_date=request.POST.get("end_date"), is_current=bool(request.POST.get("is_current")))
        try:
            year.full_clean(); year.save()
            messages.success(request, "Academic year created.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, "organizations/admin/academic/year_form.html", {"org": request.organization})


@org_admin_required
def class_create(request, slug):
    if request.method == "POST":
        obj = OrganizationClass(organization=request.organization, name=request.POST.get("name", "").strip(), code=request.POST.get("code", "").strip(), description=request.POST.get("description", "").strip())
        try:
            obj.full_clean(); obj.save()
            messages.success(request, "Class created.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, "organizations/admin/academic/class_form.html", {"org": request.organization})


@org_admin_required
def section_create(request, slug):
    if request.method == "POST":
        year = get_object_or_404(AcademicYear, id=request.POST.get("academic_year"), organization=request.organization)
        klass = get_object_or_404(OrganizationClass, id=request.POST.get("class_group"), organization=request.organization)
        obj = ClassSection(organization=request.organization, academic_year=year, class_group=klass, name=request.POST.get("name", "").strip(), capacity=request.POST.get("capacity") or None)
        try:
            obj.full_clean(); obj.save()
            messages.success(request, "Class section created.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            messages.error(request, str(exc))
    return render(request, "organizations/admin/academic/section_form.html", {"org": request.organization, "years": request.organization.academic_years.all(), "classes": request.organization.classes.filter(is_active=True)})


@org_admin_required
def teacher_assign(request, slug, section_id):
    section = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    if request.method == "POST":
        teacher = get_object_or_404(request.organization.members.select_related("user"), user_id=request.POST.get("teacher"), role="staff", is_active=True).user
        year = get_object_or_404(AcademicYear, id=request.POST.get("academic_year"), organization=request.organization)
        try:
            assign_teacher_to_section(actor=request.user, teacher=teacher, section=section, academic_year=year, subject=request.POST.get("subject"))
            messages.success(request, "Teacher assigned.")
        except Exception as exc:
            messages.error(request, str(exc))
    return redirect("organizations_admin:academic", slug=slug)


@org_teacher_required
def student_enroll(request, slug, student_id, section_id):
    student = get_object_or_404(OrganizationStudent, id=student_id, organization=request.organization)
    section = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    if request.method == "POST":
        try:
            enroll_student(actor=request.user, student=student, section=section, roll_number=request.POST.get("roll_number"))
            messages.success(request, "Student enrolled in class.")
        except Exception as exc:
            messages.error(request, str(exc))
    return redirect("organizations_admin:academic", slug=slug)
