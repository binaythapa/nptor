from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm
from quiz.track_forms import TrackExamFormSet


def _track_formset(request, track, organization):
    return TrackExamFormSet(
        request.POST or None,
        instance=track,
        organization=organization,
        prefix="track_exams",
    )


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
    if request.method == "POST":
        form = ExamTrackForm(request.POST, organization=org)
        if form.is_valid():
            track = form.save(commit=False)
            track.organization = org
            track.save()
            return redirect("organizations_admin:org_track_list", slug=slug)
    else:
        form = ExamTrackForm(organization=org)
    return render(
        request,
        "organizations/admin/tracks/create.html",
        {"form": form, "org": org},
    )


@org_admin_required
def org_track_edit(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    if request.method == "POST":
        form = ExamTrackForm(request.POST, instance=track, organization=org)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.organization = org
            updated.save()
            return redirect("organizations_admin:org_track_list", slug=slug)
    else:
        form = ExamTrackForm(instance=track, organization=org)
    return render(
        request,
        "organizations/admin/tracks/edit.html",
        {"form": form, "track": track, "org": org},
    )


@require_POST
@org_admin_required
def org_track_delete(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    track.delete()
    return redirect("organizations_admin:org_track_list", slug=slug)
