from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from quiz.forms import ExamForm
from quiz.models import Exam


@staff_member_required
def admin_exam_list(request):
    exams = Exam.objects.select_related("organization", "primary_category").prefetch_related(
        "categories", "track_memberships__track"
    ).order_by("-created_at")
    return render(request, "quiz/student/subscription/exam_list.html", {"exams": exams})


@staff_member_required
def admin_exam_create(request):
    form = ExamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        exam = form.save(commit=False)
        exam.created_by = request.user
        exam.save()
        form.save_m2m()
        return redirect("quiz:admin_exam_list")
    return render(request, "quiz/student/subscription/exam_form.html", {"form": form, "mode": "create"})


@staff_member_required
def admin_exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    form = ExamForm(request.POST or None, instance=exam)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("quiz:admin_exam_list")
    return render(request, "quiz/student/subscription/exam_form.html", {"form": form, "mode": "edit"})


@staff_member_required
def admin_exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam.delete()
    return redirect("quiz:admin_exam_list")
