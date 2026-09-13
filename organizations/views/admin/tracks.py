from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import ExamTrack, TrackExam
from quiz.forms import ExamTrackForm
from quiz.track_forms import TrackExamFormSet


def _track_formset(request, track, organization):
    return TrackExamFormSet(
        request.POST or None,
        instance=track,
        organization=organization,
        prefix="track_exams",
    )


def _organization_exams_are_valid(form, organization):
    exams = list(form.cleaned_data.get("exams") or [])
    invalid = [exam for exam in exams if exam.organization_id != organization.id]
    if invalid:
        form.add_error(
            "exams",
            "Organization Tracks can only contain Exams created by this organization.",
        )
        return False
    return True


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
    track = ExamTrack(organization=org)
    form = ExamTrackForm(request.POST or None, instance=track, organization=org)
    formset = _track_formset(request, track, org)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        track = form.save(commit=False)
        track.organization = org
        track.save()
        formset.instance = track
        formset.save()
        messages.success(request, f'Track "{track.title}" created successfully with its exam progression rules.')
        return redirect("organizations_admin:org_track_list", slug=slug)

    return render(
        request,
        "organizations/admin/tracks/create.html",
        {"form": form, "formset": formset, "org": org},
    )


@org_admin_required
def org_track_edit(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    form = ExamTrackForm(request.POST or None, instance=track, organization=org)
    formset = _track_formset(request, track, org)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        updated = form.save(commit=False)
        updated.organization = org
        updated.save()
        formset.instance = updated
        formset.save()
        messages.success(request, f'Included exams and prerequisites updated for "{track.title}".')
        return redirect("organizations_admin:org_track_list", slug=slug)

    return render(
        request,
        "organizations/admin/tracks/edit.html",
        {"form": form, "formset": formset, "track": track, "org": org},
    )


@org_admin_required
def org_track_exams(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    formset = _track_formset(request, track, org)
    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, f'Included exams and prerequisites updated for "{track.title}".')
        return redirect("organizations_admin:org_track_list", slug=slug)
    return render(
        request,
        "organizations/admin/tracks/exams.html",
        {"formset": formset, "track": track, "org": org},
    )


@require_POST
@org_admin_required
def org_track_delete(request, slug, pk):
    org = request.organization
    track = get_object_or_404(ExamTrack, pk=pk, organization=org)
    track.delete()
    return redirect("organizations_admin:org_track_list", slug=slug)
