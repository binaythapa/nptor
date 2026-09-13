from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models

from quiz.forms import ExamCategoryAllocationFormSet, ExamForm
from quiz.models import Category, Exam



def _allocation_categories(exam):
    queryset = Category.objects.filter(is_active=True).select_related("domain", "parent").order_by(
        "domain__name", "parent__name", "name"
    )
    if exam.organization_id:
        queryset = queryset.filter(models.Q(organization_id=exam.organization_id) | models.Q(organization__isnull=True))
    else:
        queryset = queryset.filter(organization__isnull=True)
    return queryset


def _bind_exam_organization(form, exam):
    """Prime an unsaved exam with the submitted organization for formset scoping."""
    organization_id = form.data.get("organization") if form.is_bound else None
    if organization_id:
        try:
            exam.organization_id = int(organization_id)
        except (TypeError, ValueError):
            pass


@staff_member_required
def admin_exam_list(request):
    exams = Exam.objects.select_related("organization").prefetch_related(
        "categories", "track_memberships__track"
    ).order_by("-created_at")
    return render(request, "quiz/student/subscription/exam_list.html", {"exams": exams})


@staff_member_required
def admin_exam_create(request):
    form = ExamForm(request.POST or None)
    exam = form.instance
    _bind_exam_organization(form, exam)
    formset = ExamCategoryAllocationFormSet(
        request.POST or None,
        instance=exam,
        category_queryset=_allocation_categories(exam),
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        exam = form.save(commit=False)
        exam.created_by = request.user
        exam.save()
        form.save_m2m()
        formset.instance = exam
        formset.save()
        return redirect("quiz:admin_exam_list")
    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {"form": form, "formset": formset, "mode": "create"},
    )


@staff_member_required
def admin_exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    form = ExamForm(request.POST or None, instance=exam)
    if request.method == "POST":
        _bind_exam_organization(form, exam)
    formset = ExamCategoryAllocationFormSet(
        request.POST or None,
        instance=exam,
        category_queryset=_allocation_categories(exam),
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        return redirect("quiz:admin_exam_list")
    return render(
        request,
        "quiz/student/subscription/exam_form.html",
        {"form": form, "formset": formset, "mode": "edit"},
    )


@staff_member_required
def admin_exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam.delete()
    return redirect("quiz:admin_exam_list")
