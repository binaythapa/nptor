from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import Exam
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
    Create a new exam for the organization.
    """

    org = request.organization

    if request.method == "POST":

        form = ExamForm(request.POST, organization=org)

        if form.is_valid():

            exam = form.save(commit=False)
            exam.organization = org
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
    Update an existing exam belonging to the organization.
    """

    org = request.organization

    exam = get_object_or_404(
        Exam,
        pk=pk,
        organization=org,
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
@require_POST
@org_admin_required
def org_exam_delete(request, slug, pk):
    """
    Delete an exam belonging to the organization.
    """

    org = request.organization

    exam = get_object_or_404(
        Exam,
        pk=pk,
        organization=org,
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