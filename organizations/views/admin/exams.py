from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import Exam, UserExam
from quiz.forms import ExamForm


# ============================================================
# EXAM LIST
# ============================================================
@org_admin_required
def org_exam_list(request, slug):
    """
    Display all exams belonging to the current organization.
    """

    org = request.organization

    exams = (
        Exam.objects
        .filter(organization=org)
        .select_related("track", "category")
        .order_by("-created_at")
    )

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
@org_admin_required
def org_exam_create(request, slug):
    """
    Create a new unpublished exam for the organization.

    Organization admins may configure an exam, but publishing is
    intentionally reserved for the platform moderation boundary.
    """

    org = request.organization

    if request.method == "POST":

        form = ExamForm(request.POST, organization=org)

        if form.is_valid():

            exam = form.save(commit=False)
            exam.organization = org
            # Never allow an organization-admin form submission to
            # publish an exam by tampering with is_published.
            exam.is_published = False
            exam.save()

            # save ManyToMany fields
            form.save_m2m()

            messages.success(request, "Exam created successfully.")

            return redirect(
                "organizations_admin:exams",
                slug=slug,
            )

    else:
        form = ExamForm(organization=org)

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
@org_admin_required
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

    if exam.is_published:
        return _forbidden_exam_mutation(
            request,
            "Published exams cannot be modified by organization admins.",
        )

    if request.method == "POST":

        form = ExamForm(
            request.POST,
            instance=exam,
            organization=org,
        )

        if form.is_valid():

            exam = form.save(commit=False)
            exam.organization = org
            # Publishing is not an organization-admin capability.
            exam.is_published = False
            exam.save()

            form.save_m2m()

            messages.success(request, "Exam updated successfully.")

            return redirect(
                "organizations_admin:exams",
                slug=slug,
            )

    else:
        form = ExamForm(
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
@org_admin_required
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

    if exam.is_published:
        return _forbidden_exam_mutation(
            request,
            "Published exams cannot be deleted by organization admins.",
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