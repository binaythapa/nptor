from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm
from organizations.forms.track import TrackExamFormSet


def _track_formset(request, track=None):
    return TrackExamFormSet(
        request.POST or None,
        instance=track,
        prefix="track_exams",
        organization=request.organization,
    )


def _save_track(request, form, formset, org, track=None):
    with transaction.atomic():
        track = form.save(commit=False)
        track.organization = org
        track.save()
        formset.instance = track
        formset.save()
    return track


@org_admin_required
def org_track_list(request, slug):
    org = request.organization
    tracks = ExamTrack.objects.filter(organization=org).prefetch_related("track_exams__exam").order_by("-created_at")
    return render(
        request,
        "organizations/admin/tracks/list.html",
        {"tracks": tracks, "org": org},
    )


@org_admin_required
def org_track_create(request, slug):
    org = request.organization
    form = ExamTrackForm(request.POST or None)
    formset = _track_formset(request)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        _save_track(request, form, formset, org)
        return redirect("organizations_admin:org_track_list", slug=slug)
    return render(
        request,
        "organizations/admin/tracks/create.html",
        {"form": form, "track_exams": formset, "org": org},
    )


@org_admin_required
def org_track_edit(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    form = ExamTrackForm(request.POST or None, instance=track)
    formset = _track_formset(request, track=track)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        _save_track(request, form, formset, org, track=track)
        return redirect("organizations_admin:org_track_list", slug=slug)
    return render(
        request,
        "organizations/admin/tracks/edit.html",
        {"form": form, "track_exams": formset, "track": track, "org": org},
    )


@require_POST
@org_admin_required
def org_track_delete(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    track.delete()
    return redirect("organizations_admin:org_track_list", slug=slug)
