from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from quiz.models import Exam
from quiz.forms import ExamForm
from courses.models import Course

@staff_member_required
def admin_exam_list(request):
    exams = Exam.objects.all().order_by("-created_at")
    courses = Course.objects.filter(is_published=True)

    return render(request, "quiz/student/subscription/exam_list.html", {
    "track_map": track_map,
    "courses": courses,   # 👈 ADD THIS
})


@staff_member_required
def admin_exam_create(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("quiz:admin_exam_list")
    else:
        form = ExamForm()

    return render(request, "quiz/student/subscription/exam_form.html", {
        "form": form,
        "title": "Create Exam",
    })


@staff_member_required
def admin_exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)

    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            return redirect("quiz:admin_exam_list")
    else:
        form = ExamForm(instance=exam)

    return render(request, "quiz/student/subscription/exam_form.html", {
        "form": form,
        "title": "Edit Exam",
    })


@staff_member_required
def admin_exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam.delete()
    return redirect("quiz:admin_exam_list")


from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm


@staff_member_required
def admin_track_list(request):
    tracks = ExamTrack.objects.all().order_by("-created_at")
    return render(request, "quiz/student/subscription/track_list.html", {"tracks": tracks})


@staff_member_required
def admin_track_create(request):
    if request.method == "POST":
        form = ExamTrackForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("quiz:admin_track_list")
    else:
        form = ExamTrackForm()

    return render(request, "quiz/student/subscription/track_form.html", {
        "form": form,
        "title": "Create Track",
    })


@staff_member_required
def admin_track_update(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)

    if request.method == "POST":
        form = ExamTrackForm(request.POST, instance=track)
        if form.is_valid():
            form.save()
            return redirect("quiz:admin_track_list")
    else:
        form = ExamTrackForm(instance=track)

    return render(request, "quiz/student/subscription/track_form.html", {
        "form": form,
        "title": "Edit Track",
    })


@staff_member_required
def admin_track_delete(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    track.delete()
    return redirect("quiz:admin_track_list")
