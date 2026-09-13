from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import ExamTrack
from quiz.track_forms import TrackExamFormSet
from quiz.views.admin_subscription_views import TrackForm


def _track_formset(request, instance, organization):
    return TrackExamFormSet(
        request.POST or None,
        instance=instance,
        organization=organization,
        prefix="track_exams",
    )


@staff_member_required
def admin_track_create(request):
    form = TrackForm(request.POST or None)
    organization = None
    if request.method == "POST" and form.is_valid():
        organization = form.cleaned_data.get("organization")
    formset = _track_formset(request, ExamTrack(), organization)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
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
    form = TrackForm(request.POST or None, instance=track, organization=track.organization)
    organization = track.organization
    if request.method == "POST" and form.is_valid():
        organization = form.cleaned_data.get("organization")
    formset = _track_formset(request, track, organization)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            track = form.save(commit=False)
            track.save()
            form.save_m2m()
            formset.instance = track
            formset.save()
        return redirect("quiz:admin_track_list")

    return render(
        request,
        "quiz/student/subscription/track_form.html",
        {"form": form, "formset": formset, "mode": "edit"},
    )
