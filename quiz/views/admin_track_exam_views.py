from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import ExamTrack
from quiz.track_forms import TrackExamFormSet


@staff_member_required
def admin_track_exams(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    organization = track.organization
    formset = TrackExamFormSet(
        request.POST or None,
        instance=track,
        organization=organization,
        prefix="track_exams",
    )

    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, f'Included exams and prerequisites updated for "{track.title}".')
        return redirect("quiz:admin_track_update", pk=track.pk)

    return render(
        request,
        "quiz/student/subscription/track_exams.html",
        {"track": track, "formset": formset},
    )
