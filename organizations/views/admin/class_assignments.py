from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course
from quiz.models import Exam, ExamTrack
from organizations.models import ClassResourceAssignment, ClassSection
from organizations.models.role import OrganizationRole
from organizations.permissions import org_teacher_required
from organizations.services.class_assignments import assign_class_resource


@org_teacher_required
def class_assignment_create(request, slug, section_id):
    section = get_object_or_404(ClassSection.objects.select_related("academic_year", "class_group"), id=section_id, organization=request.organization, is_active=True)
    if request.method == "POST":
        resource_type = request.POST.get("resource_type")
        resource_id = request.POST.get("resource_id")
        resource = None
        if resource_type == ClassResourceAssignment.RESOURCE_COURSE:
            resource = get_object_or_404(Course, id=resource_id)
        elif resource_type == ClassResourceAssignment.RESOURCE_TRACK:
            resource = get_object_or_404(ExamTrack, id=resource_id)
        elif resource_type == ClassResourceAssignment.RESOURCE_EXAM:
            resource = get_object_or_404(Exam, id=resource_id, organization=request.organization)
        try:
            assign_class_resource(actor=request.user, section=section, resource_type=resource_type, resource=resource)
            messages.success(request, "Resource assigned to the class.")
            return redirect("organizations_admin:academic", slug=slug)
        except Exception as exc:
            messages.error(request, str(exc))
    context = {
        "org": request.organization,
        "section": section,
        "courses": Course.objects.filter(organization_subscriptions__organization=request.organization, organization_subscriptions__is_active=True).distinct().order_by("title"),
        "tracks": ExamTrack.objects.filter(organization=request.organization).order_by("title"),
        "exams": Exam.objects.filter(organization=request.organization).order_by("title"),
    }
    return render(request, "organizations/admin/academic/class_assignment_form.html", context)
