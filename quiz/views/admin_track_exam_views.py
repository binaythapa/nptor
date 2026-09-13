from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from quiz.models import Exam, ExamTrack


class TrackExamAssignmentForm(forms.Form):
    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 12, "class": "admin-exam-select"}),
        label="Included Exams",
        help_text="Select the reusable exams included in this Track. Exams are never sold separately.",
    )

    def __init__(self, *args, track=None, **kwargs):
        super().__init__(*args, **kwargs)
        exam_qs = Exam.objects.filter(is_published=True).order_by("title")
        if track and track.organization_id:
            exam_qs = exam_qs.filter(
                Q(organization_id=track.organization_id) | Q(organization__isnull=True)
            )
        self.fields["exams"].queryset = exam_qs
        if track:
            self.fields["exams"].initial = track.track_exams.values_list("exam_id", flat=True)


@staff_member_required
def admin_track_exams(request, pk):
    track = get_object_or_404(ExamTrack, pk=pk)
    form = TrackExamAssignmentForm(request.POST or None, track=track)
    if request.method == "POST" and form.is_valid():
        track.exams.set(form.cleaned_data["exams"])
        messages.success(request, f'Included exams updated for "{track.title}".')
        return redirect("quiz:admin_track_update", pk=track.pk)
    return render(
        request,
        "quiz/student/subscription/track_exams.html",
        {"track": track, "form": form},
    )
