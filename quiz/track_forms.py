from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from quiz.models import Exam, ExamTrack, TrackExam
from quiz.search_widgets import SearchableModelChoiceWidget, SearchableModelMultipleChoiceWidget


class TrackExamAssignmentForm(forms.ModelForm):
    class Meta:
        model = TrackExam
        fields = ["exam", "order", "is_required", "prerequisite_exams"]
        widgets = {
            "exam": SearchableModelChoiceWidget(),
            "prerequisite_exams": SearchableModelMultipleChoiceWidget(
                attrs={
                    "data-autocomplete-scope": "exams",
                    "data-search-placeholder": "Search prerequisite exams...",
                }
            ),
        }

    def __init__(self, *args, exam_queryset=None, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = (exam_queryset if exam_queryset is not None else Exam.objects.filter(is_published=True)).order_by("title")
        self.fields["exam"].queryset = qs
        self.fields["prerequisite_exams"].queryset = qs
        self.fields["prerequisite_exams"].help_text = (
            "Optional exams that must be passed before this exam becomes available in the Track."
        )
        if organization is not None:
            org_id = str(organization.pk)
            self.fields["exam"].widget.attrs["data-autocomplete-organization"] = org_id
            self.fields["prerequisite_exams"].widget.attrs["data-autocomplete-organization"] = org_id


class TrackExamInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, organization=None, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)

        qs = Exam.objects.filter(is_published=True)
        if organization is not None:
            qs = qs.filter(organization=organization)
        else:
            qs = qs.filter(organization__isnull=True)
        self.exam_queryset = qs.order_by("title")

        for form in self.forms:
            form.fields["exam"].queryset = self.exam_queryset
            form.fields["prerequisite_exams"].queryset = self.exam_queryset
            if organization is not None:
                org_id = str(organization.pk)
                form.fields["exam"].widget.attrs["data-autocomplete-organization"] = org_id
                form.fields["prerequisite_exams"].widget.attrs["data-autocomplete-organization"] = org_id

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        selected_exam_ids = set()
        rows = []
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            exam = form.cleaned_data.get("exam")
            if not exam:
                continue
            if exam.pk in selected_exam_ids:
                form.add_error("exam", "An exam can only be added to a Track once.")
            selected_exam_ids.add(exam.pk)
            rows.append((form, exam))

        for form, exam in rows:
            prerequisites = form.cleaned_data.get("prerequisite_exams") or []
            if exam in prerequisites:
                form.add_error("prerequisite_exams", "An exam cannot be a prerequisite of itself.")
            invalid = [item for item in prerequisites if item.pk not in selected_exam_ids]
            if invalid:
                form.add_error(
                    "prerequisite_exams",
                    "Prerequisite exams must also be included in this Track.",
                )


TrackExamFormSet = inlineformset_factory(
    ExamTrack,
    TrackExam,
    form=TrackExamAssignmentForm,
    formset=TrackExamInlineFormSet,
    extra=1,
    can_delete=True,
)
