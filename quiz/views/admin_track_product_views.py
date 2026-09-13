from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import ExamTrack
from quiz.track_forms import TrackExamFormSet
from quiz.views.admin_subscription_views import TrackForm


@staff_member_required
def admin_track_create(request):
    organization = None
    form = TrackForm(request.POST or None, organization=organization)
    formset = TrackExamFormSet(
        request.POST or None,
        instance=ExamTrack(),
        organization=organization,
        prefix="track_exams",
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        track = form.save(commit=False)
        track.save()
        form.save_m2m()
        formset.instance = track
        formset.save()
        return redirect("quiz:admin_track_list")

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {"form": form, "formset": formset, "mode": "create"},
    )


@staff_member_required
def admin_track_update(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    organization = track.organization
    form = TrackForm(request.POST or None, instance=track, organization=organization)
    formset = TrackExamFormSet(
        request.POST or None,
        instance=track,
        organization=organization,
        prefix="track_exams",
    )

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save(commit=True)
        formset.save()
        return redirect("quiz:admin_track_list")

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {"form": form, "formset": formset, "mode": "edit"},
    )
