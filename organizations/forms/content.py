from django import forms
from django.db.models import Q

from courses.forms import save_course_exams
from courses.models import Course
from quiz.models import Category, Exam, ExamTrack
from quiz.search_widgets import SearchableModelMultipleChoiceWidget


class OrganizationCourseForm(forms.ModelForm):
    """Create/edit a private course owned by the active organization."""

    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=SearchableModelMultipleChoiceWidget(
            attrs={
                "data-autocomplete-scope": "exams",
                "data-search-placeholder": "Search exams...",
            }
        ),
        help_text="Select the reusable exams included in this course.",
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "category",
            "thumbnail",
            "level",
            "exams",
        ]

    def __init__(self, *args, organization=None, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)

        organization_scope = Q(organization=organization) | Q(organization__isnull=True)
        category_qs = Category.objects.filter(
            organization_scope,
            is_active=True,
        ).select_related("domain", "parent").order_by(
            "domain__name", "parent__name", "name"
        )
        exam_qs = Exam.objects.filter(
            organization_scope,
            is_published=True,
        ).order_by("title")

        self.fields["category"].queryset = category_qs
        self.fields["exams"].queryset = exam_qs
        if organization is not None:
            self.fields["exams"].widget.attrs["data-autocomplete-organization"] = str(organization.pk)
        if self.instance.pk:
            self.fields["exams"].initial = self.instance.course_exams.values_list(
                "exam_id",
                flat=True,
            )

    def clean(self):
        cleaned = super().clean()
        organization_id = getattr(self.organization, "id", None)
        exams = cleaned.get("exams") or []
        invalid = [exam for exam in exams if exam.organization_id not in (None, organization_id)]
        if invalid:
            self.add_error("exams", "Course exams must belong to this organization or be global exams.")
        category = cleaned.get("category")
        if category and category.organization_id not in (None, organization_id):
            self.add_error("category", "Course category must belong to this organization or be global.")
        return cleaned

    def save(self, commit=True):
        course = super().save(commit=False)
        course.organization = self.organization
        course.owner_type = Course.OWNER_ORGANIZATION
        course.is_public = False
        course.is_published = False
        if commit:
            course.save()
            self.save_m2m()
            save_course_exams(
                course,
                self.cleaned_data.get("exams") or [],
            )
        return course


class OrganizationExamTrackForm(forms.ModelForm):
    """Create/edit a private organization Track without commerce fields."""

    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
        help_text="Select the reusable exams included in this Track.",
    )

    class Meta:
        model = ExamTrack
        fields = [
            "title",
            "slug",
            "description",
            "exams",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "textarea"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        self.organization = organization
        super().__init__(*args, **kwargs)
        exam_qs = Exam.objects.filter(
            organization=organization,
            is_published=True,
        ).order_by("title")
        self.fields["exams"].queryset = exam_qs
        if self.instance.pk:
            self.fields["exams"].initial = self.instance.track_exams.values_list("exam_id", flat=True)

    def clean(self):
        cleaned = super().clean()
        exams = cleaned.get("exams") or []
        invalid = [exam for exam in exams if exam.organization_id != getattr(self.organization, "id", None)]
        if invalid:
            self.add_error("exams", "Organization Tracks can only contain Exams created by this organization.")
        return cleaned

    def save(self, commit=True):
        track = super().save(commit=False)
        track.organization = self.organization
        track.subscription_scope = ExamTrack.TRACK
        if commit:
            track.save()
            self.save_m2m()
        return track
