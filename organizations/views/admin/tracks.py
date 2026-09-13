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


def _save_selected_exams(track, exams):
    selected = list(exams or [])
    selected_ids = {exam.pk for exam in selected}
    TrackExam.objects.filter(track=track).exclude(exam_id__in=selected_ids).delete()
    existing = {row.exam_id: row for row in TrackExam.objects.filter(track=track)}
    for order, exam in enumerate(selected, start=1):
        row = existing.get(exam.pk)
        if row is None:
            TrackExam.objects.create(track=track, exam=exam, order=order)
        elif row.order != order:
            row.order = order
            row.save(update_fields=["order"])


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
    if request.method == "POST":
        form = ExamTrackForm(request.POST, organization=org)
        if form.is_valid() and _organization_exams_are_valid(form, org):
            track = form.save(commit=False)
            track.organization = org
            track.save()
            _save_selected_exams(track, form.cleaned_data.get("exams"))
            return redirect("organizations_admin:org_track_exams", slug=slug, pk=track.pk)
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
        if form.is_valid() and _organization_exams_are_valid(form, org):
            updated = form.save(commit=False)
            updated.organization = org
            updated.save()
            _save_selected_exams(track, form.cleaned_data.get("exams"))
            return redirect("organizations_admin:org_track_exams", slug=slug, pk=track.pk)
    else:
        form = ExamTrackForm(instance=track, organization=org)
    return render(
        request,
        "organizations/admin/tracks/edit.html",
        {"form": form, "track": track, "org": org},
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
