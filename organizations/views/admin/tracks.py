from django.shortcuts import render, redirect, get_object_or_404
from organizations.permissions import org_admin_required
from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm


from django.shortcuts import render, redirect, get_object_or_404
from organizations.permissions import org_admin_required
from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm


@org_admin_required
def org_track_list(request, slug):

    org = request.organization

    tracks = ExamTrack.objects.filter(
        organization=org
    ).order_by("-created_at")

    return render(
        request,
        "organizations/admin/tracks/list.html",
        {
            "tracks": tracks,
            "org": org,
        }
    )




@org_admin_required
def org_track_create(request, slug):

    org = request.organization

    if request.method == "POST":

        form = ExamTrackForm(request.POST)

        if form.is_valid():

            track = form.save(commit=False)
            track.organization = org
            track.save()

            return redirect(
                "organizations_admin:org_track_list",
                slug=slug
            )

    else:
        form = ExamTrackForm()

    return render(
        request,
        "organizations/admin/tracks/create.html",
        {
            "form": form,
            "org": org,
        }
    )


from django.shortcuts import render, redirect, get_object_or_404
from organizations.permissions import org_admin_required
from quiz.models import ExamTrack
from quiz.forms import ExamTrackForm


@org_admin_required
def org_track_edit(request, slug, pk):

    org = request.organization

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
        organization=org
    )

    if request.method == "POST":
        form = ExamTrackForm(request.POST, instance=track)

        if form.is_valid():
            form.save()
            return redirect("organizations_admin:org_track_list", slug=slug)

    else:
        form = ExamTrackForm(instance=track)

    return render(
        request,
        "organizations/admin/tracks/edit.html",
        {
            "form": form,
            "track": track
        }
    )


@org_admin_required
def org_track_delete(request, slug, pk):

    org = request.organization

    track = get_object_or_404(
        ExamTrack,
        pk=pk,
        organization=org
    )

    track.delete()

    return redirect(
        "organizations_admin:org_track_list",
        slug=slug
    )