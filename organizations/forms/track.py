from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from quiz.models import Exam, ExamTrack, TrackExam


class TrackExamForm(forms.ModelForm):
    class Meta:
        model = TrackExam
        fields = ("exam", "order", "is_required", "prerequisite_exams")
        widgets = {
            "prerequisite_exams": forms.SelectMultiple(
                attrs={"class": "track-prerequisite-select"}
            ),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        exam_qs = Exam.objects.filter(
            Q(organization=organization) | Q(organization__isnull=True)
        ).order_by("title")
        self.fields["exam"].queryset = exam_qs
        self.fields["prerequisite_exams"].queryset = exam_qs
        self.fields["exam"].widget.attrs.update({"class": "track-exam-select"})
        self.fields["order"].widget.attrs.update({"class": "input", "min": 1})
        self.fields["is_required"].widget.attrs.update({"class": "checkbox"})


class BaseTrackExamFormSet(BaseInlineFormSet):
    def __init__(self, *args, organization=None, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)
        exam_qs = Exam.objects.filter(
            Q(organization=organization) | Q(organization__isnull=True)
        ).order_by("title")
        for form in self.forms:
            form.organization = organization
            form.fields["exam"].queryset = exam_qs
            form.fields["prerequisite_exams"].queryset = exam_qs

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        rows = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        exams = [row.get("exam") for row in rows if row.get("exam")]
        exam_ids = [exam.pk for exam in exams]
        if len(exam_ids) != len(set(exam_ids)):
            raise ValidationError("An exam can only be added once to a track.")

        allowed_ids = set(exam_ids)
        graph = {exam_id: set() for exam_id in allowed_ids}
        for row in rows:
            exam = row.get("exam")
            if not exam:
                continue
            prerequisites = row.get("prerequisite_exams") or []
            prerequisite_ids = {item.pk for item in prerequisites}
            invalid = prerequisite_ids - allowed_ids
            if invalid:
                raise ValidationError("Every prerequisite must also be included in this track.")
            if exam.pk in prerequisite_ids:
                raise ValidationError("An exam cannot be its own prerequisite.")
            graph[exam.pk] = prerequisite_ids

        visiting = set()
        visited = set()

        def visit(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            if any(visit(parent) for parent in graph.get(node, ())):
                return True
            visiting.remove(node)
            visited.add(node)
            return False

        if any(visit(node) for node in graph):
            raise ValidationError("Track exam prerequisites cannot contain a circular dependency.")


TrackExamFormSet = inlineformset_factory(
    ExamTrack,
    TrackExam,
    form=TrackExamForm,
    formset=BaseTrackExamFormSet,
    extra=1,
    can_delete=True,
)
