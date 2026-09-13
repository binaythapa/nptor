from django import forms
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Q

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Course, CourseSection, Lesson, CourseExam
from quiz.models import Category, Exam
from quiz.search_widgets import SearchableModelMultipleChoiceWidget
from subscriptions.models import SubscriptionPlan


def save_course_exams(course, exams):
    """Synchronize a course's reusable exam memberships."""
    selected_exams = list(exams or [])
    selected_ids = {exam.pk for exam in selected_exams}

    with transaction.atomic():
        CourseExam.objects.filter(course=course).exclude(
            exam_id__in=selected_ids,
        ).delete()

        existing = {
            membership.exam_id: membership
            for membership in CourseExam.objects.filter(course=course)
        }

        for order, exam in enumerate(selected_exams, start=1):
            membership = existing.get(exam.pk)
            if membership is None:
                CourseExam.objects.create(
                    course=course,
                    exam=exam,
                    order=order,
                )
            elif membership.order != order:
                membership.order = order
                membership.save(update_fields=["order"])


class CourseForm(forms.ModelForm):

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "textarea"
            }
        )
    )

    exams = forms.ModelMultipleChoiceField(
        queryset=Exam.objects.none(),
        required=False,
        widget=SearchableModelMultipleChoiceWidget(
            attrs={"data-autocomplete-scope": "exams"}
        ),
        help_text="Search by exam title and select the reusable exams included in this course. Exams are not sold separately.",
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "category",
            "thumbnail",
            "level",
            "subscription_plans",
            "exams",
            "is_public",
            "is_published",
        ]

        widgets = {
            "subscription_plans": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop("organization", None)
        super().__init__(*args, **kwargs)

        if organization is not None:
            self.fields["category"].queryset = Category.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_active=True,
            ).order_by("name")
            self.fields["exams"].queryset = Exam.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_published=True,
            ).order_by("title")
            self.fields["exams"].widget.attrs["data-autocomplete-organization"] = str(organization.pk)
        else:
            self.fields["exams"].queryset = Exam.objects.filter(
                is_published=True
            ).order_by("title")

        self.fields["subscription_plans"].queryset = SubscriptionPlan.objects.filter(
            is_active=True,
            product_type=SubscriptionPlan.PRODUCT_COURSE,
            access_mode=SubscriptionPlan.ACCESS_SINGLE_RESOURCE,
        ).order_by("price", "name")
        self.fields["subscription_plans"].help_text = (
            "Course product plans only. Buying a course grants this course and its included exams."
        )

        if self.instance.pk:
            self.fields["exams"].initial = self.instance.course_exams.values_list(
                "exam_id",
                flat=True,
            )

    def save(self, commit=True):
        course = super().save(commit=commit)
        if commit:
            save_course_exams(
                course,
                self.cleaned_data.get("exams") or [],
            )
        return course


CourseSectionFormSet = inlineformset_factory(
    Course,
    CourseSection,
    fields=[
        "title",
        "order",
    ],
    extra=1,
    can_delete=True
)


class LessonForm(forms.ModelForm):

    article_content = forms.CharField(
        widget=CKEditorUploadingWidget(config_name="default"),
        required=False
    )

    class Meta:
        model = Lesson
        exclude = (
            "section",
            "order",
            "is_deleted",
            "created_at",
            "updated_at",
        )
