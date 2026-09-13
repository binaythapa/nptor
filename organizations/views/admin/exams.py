from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms import HiddenInput
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_teacher_required
from organizations.models.role import OrganizationRole
from organizations.services.content_permissions import user_can_manage_owned_content
from quiz.models import Exam, UserExam, Category
from quiz.forms import ExamForm


class OrganizationExamForm(ExamForm):
    """Global exam form layout with organization-only classification choices."""

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, organization=organization, **kwargs)
        if organization is None:
            return

        category_qs = (
            Category.objects
            .filter(organization=organization, is_active=True)
            .select_related("domain", "parent")
            .order_by("domain__name", "parent__name", "name")
        )
        self.fields["primary_category"].queryset = category_qs
        self.fields["categories"].queryset = category_qs

        self.fields["organization"].queryset = type(self.fields["organization"].queryset).filter(
            self.fields["organization"].queryset,
            pk=organization.pk,
        )
        self.fields["organization"].initial = organization
        self.fields["organization"].required = True
        self.fields["organization"].widget = HiddenInput()

        self.fields["primary_category"].widget.attrs["data-autocomplete-organization-only"] = "true"
        self.fields["categories"].widget.attrs["data-autocomplete-organization-only"] = "true"
        self.fields["categories"].help_text = "Search and select categories belonging to this organization."
        self.fields["primary_category"].help_text = "Select the main category from this organization's category catalog."

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        if organization is not None and self.fields["organization"].queryset.filter(pk=organization.pk).exists() is False:
            self.add_error("organization", "Invalid organization.")
        return cleaned_data


# ============================================================
# EXAM LIST
# ============================================================
@org_teacher_required
def org_exam_list(request, slug):
    """
    Display exams available to the current organization member.

    Staff/teachers see only exams they created. Owners/admins retain the
    organization-wide view.
    """

    org = request.organization

    exams = (
        Exam.objects
        .filter(organization=org)
        .select_related("primary_category")
        .order_by("-created_at")
    )
    if request.organization_member.role == OrganizationRole.STAFF:
        exams = exams.filter(created_by=request.user)

    return render(
        request,
        "organizations/admin/exams/list.html",
        {
            "exams": exams,
            "org": org,
        },
    )


# ============================================================
# CREATE EXAM
# ============================================================
@org_teacher_required
def org_exam_create(request, slug):
    """Create a new unpublished organization exam using the global admin form layout."""

    org = request.organization

    if request.method == "POST":
        form = OrganizationExamForm(request.POST, organization=org)

        if form.is_valid():
            exam = form.save(commit=False)
            exam.organization = org
            exam.created_by = request.user
            # Organization teaching members cannot publish directly.
            exam.is_published = False
            exam.save()
            form.save_m2m()

            messages.success(request, "Exam created successfully.")
            return redirect("organizations_admin:exams", slug=slug)
    else:
        form = OrganizationExamForm(organization=org)

    return render(
        request,
        "organizations/admin/exams/create.html",
        {
            "form": form,
            "org": org,
        },
    )


# ============================================================
# UPDATE EXAM
# ============================================================
@org_teacher_required
def org_exam_update(request, slug, pk):
    """
    Update an unpublished exam belonging to the organization.

    Once an exam is published, its commercial/configuration data is
    frozen to prevent changing an exam after students may have relied
    on or purchased access to it.
    """

    org = request.organization

    exam = get_object_or_404(
        Exam,
        pk=pk,
        organization=org,
    )

    if not user_can_manage_owned_content(request.user, org, exam):
        raise PermissionDenied("You can only modify exams you created.")

    if exam.is_published:
        return _forbidden_exam_mutation(
            request,
            "Published exams cannot be modified by organization teaching members.",
        )

    if request.method == "POST":
        form = OrganizationExamForm(
            request.POST,
            instance=exam,
            organization=org,
        )

        if form.is_valid():
            exam = form.save(commit=False)
            exam.organization = org
            exam.is_published = False
            exam.save()
            form.save_m2m()

            messages.success(request, "Exam updated successfully.")
            return redirect("organizations_admin:exams", slug=slug)
    else:
        form = OrganizationExamForm(
            instance=exam,
            organization=org,
        )

    return render(
        request,
        "organizations/admin/exams/edit.html",
        {
            "form": form,
            "exam": exam,
            "org": org,
        },
    )


# ============================================================
# DELETE EXAM
# ============================================================
def _forbidden_exam_mutation(request, message):
    from django.http import HttpResponseForbidden

    return HttpResponseForbidden(message)


@require_POST
@org_teacher_required
def org_exam_delete(request, slug, pk):
    """
    Delete an organization exam only when it has no student attempt
    history. Attempt records are part of the audit trail and must not
    be destroyed by organization administration.
    """

    org = request.organization

    exam = get_object_or_404(
        Exam,
        pk=pk,
        organization=org,
    )

    if not user_can_manage_owned_content(request.user, org, exam):
        raise PermissionDenied("You can only delete exams you created.")

    if exam.is_published:
        return _forbidden_exam_mutation(
            request,
            "Published exams cannot be deleted by organization teaching members.",
        )

    if UserExam.objects.filter(exam=exam).exists():
        return _forbidden_exam_mutation(
            request,
            "Exams with attempt history cannot be deleted.",
        )

    exam_title = exam.title
    exam.delete()

    messages.success(
        request,
        f'Exam "{exam_title}" deleted successfully.',
    )

    return redirect(
        "organizations_admin:exams",
        slug=slug,
    )
