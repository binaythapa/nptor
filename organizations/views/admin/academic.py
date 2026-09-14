from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from organizations.forms.academic import AcademicYearForm, ClassSectionForm, OrganizationClassForm
from organizations.models import AcademicYear, ClassSection, ClassTeacher, OrganizationClass, OrganizationStudent
from organizations.permissions import org_admin_required, org_teacher_required
from organizations.services.enrollment import assign_teacher_to_section, enroll_student


@org_teacher_required
def academic_dashboard(request, slug):
    org = request.organization
    years = org.academic_years.all()
    classes = org.classes.all()
    sections = org.class_sections.select_related("academic_year", "class_group").prefetch_related("enrollments").all()
    if request.organization_member.role == "staff":
        sections = sections.filter(teacher_assignments__teacher=request.user, teacher_assignments__is_active=True).distinct()
    return render(request, "organizations/admin/academic/dashboard.html", {"org": org, "years": years, "classes": classes, "sections": sections})


@org_admin_required
def academic_year_create(request, slug):
    form = AcademicYearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        year = form.save(commit=False)
        year.organization = request.organization
        try:
            year.full_clean(); year.save()
            messages.success(request, "Academic year created.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/year_form.html", {"org": request.organization, "form": form, "title": "Add Academic Year"})


@org_admin_required
def academic_year_edit(request, slug, year_id):
    year = get_object_or_404(AcademicYear, id=year_id, organization=request.organization)
    form = AcademicYearForm(request.POST or None, instance=year)
    if request.method == "POST" and form.is_valid():
        try:
            year = form.save(commit=False); year.organization = request.organization; year.full_clean(); year.save()
            messages.success(request, "Academic year updated.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/year_form.html", {"org": request.organization, "form": form, "title": "Edit Academic Year", "year": year})


@org_admin_required
@require_POST
def academic_year_toggle(request, slug, year_id):
    year = get_object_or_404(AcademicYear, id=year_id, organization=request.organization)
    year.is_current = not year.is_current
    year.save(update_fields=["is_current"])
    messages.success(request, f"Academic year marked {'current' if year.is_current else 'not current'}.")
    return redirect("organizations_admin:academic", slug=slug)


@org_admin_required
def class_create(request, slug):
    form = OrganizationClassForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False); obj.organization = request.organization
        try:
            obj.full_clean(); obj.save(); messages.success(request, "Class created."); return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc: form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/class_form.html", {"org": request.organization, "form": form, "title": "Add Class"})


@org_admin_required
def class_edit(request, slug, class_id):
    obj = get_object_or_404(OrganizationClass, id=class_id, organization=request.organization)
    form = OrganizationClassForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save(commit=False); obj.organization = request.organization; obj.full_clean(); obj.save(); messages.success(request, "Class updated."); return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc: form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/class_form.html", {"org": request.organization, "form": form, "title": "Edit Class", "class_obj": obj})


@org_admin_required
@require_POST
def class_toggle(request, slug, class_id):
    obj = get_object_or_404(OrganizationClass, id=class_id, organization=request.organization)
    obj.is_active = not obj.is_active; obj.save(update_fields=["is_active"])
    messages.success(request, f"Class {'activated' if obj.is_active else 'deactivated'}.")
    return redirect("organizations_admin:academic", slug=slug)


@org_admin_required
def section_create(request, slug):
    form = ClassSectionForm(request.POST or None, organization=request.organization)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False); obj.organization = request.organization
        try:
            obj.full_clean(); obj.save(); messages.success(request, "Class section created."); return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc: form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/section_form.html", {"org": request.organization, "form": form, "title": "Add Class Section"})


@org_admin_required
def section_edit(request, slug, section_id):
    obj = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    form = ClassSectionForm(request.POST or None, instance=obj, organization=request.organization)
    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save(commit=False); obj.organization = request.organization; obj.full_clean(); obj.save(); messages.success(request, "Class section updated."); return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc: form.add_error(None, str(exc))
    return render(request, "organizations/admin/academic/section_form.html", {"org": request.organization, "form": form, "title": "Edit Class Section", "section": obj})


@org_admin_required
@require_POST
def section_toggle(request, slug, section_id):
    obj = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    obj.is_active = not obj.is_active; obj.save(update_fields=["is_active"])
    messages.success(request, f"Section {'activated' if obj.is_active else 'deactivated'}.")
    return redirect("organizations_admin:academic", slug=slug)


@org_admin_required
def teacher_assign(request, slug, section_id):
    section = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    if request.method == "POST":
        teacher = get_object_or_404(request.organization.members.select_related("user"), user_id=request.POST.get("teacher"), role="staff", is_active=True).user
        year = get_object_or_404(AcademicYear, id=request.POST.get("academic_year"), organization=request.organization)
        try:
            assign_teacher_to_section(actor=request.user, teacher=teacher, section=section, academic_year=year, subject=request.POST.get("subject")); messages.success(request, "Teacher assigned.")
        except Exception as exc: messages.error(request, str(exc))
    return redirect("organizations_admin:academic", slug=slug)


@org_teacher_required
def student_enroll(request, slug, student_id, section_id):
    student = get_object_or_404(OrganizationStudent, id=student_id, organization=request.organization)
    section = get_object_or_404(ClassSection, id=section_id, organization=request.organization)
    if request.method == "POST":
        try:
            enroll_student(actor=request.user, student=student, section=section, roll_number=request.POST.get("roll_number")); messages.success(request, "Student enrolled in class.")
        except Exception as exc: messages.error(request, str(exc))
    return redirect("organizations_admin:academic", slug=slug)
