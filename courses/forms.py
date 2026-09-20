from django import forms
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Q

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Course, CourseSection, Lesson, CourseExam
from quiz.models import Category, Domain, Exam
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
            self.fields["category"].queryset = Domain.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_active=True,
            ).order_by("name")
            self.fields["exams"].queryset = Exam.objects.filter(
                Q(organization=organization) | Q(organization__isnull=True),
                is_published=True,
            ).order_by("title")
            self.fields["exams"].widget.attrs["data-autocomplete-organization"] = str(organization.pk)
        else:
            self.fields["category"].queryset = Domain.objects.filter(
                is_active=True,
            ).order_by("name")
            self.fields["exams"].queryset = Exam.objects.filter(
                is_published=True
            ).order_by("title")

        self.fields["category"].label = "Subject / Domain"
        self.fields["category"].help_text = "Select the broad subject or domain covered by this course."

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Practice domains are restricted to active domains.
        self.fields["practice_domain"].queryset = (
            Domain.objects.filter(is_active=True).order_by("name")
        )

        # Resolve the domain from submitted form data when the form is
        # bound; otherwise use the lesson's currently saved domain.
        domain_id = None
        if self.is_bound:
            domain_id = self.data.get("practice_domain")
        elif self.instance.pk:
            domain_id = self.instance.practice_domain_id

        category_queryset = Category.objects.filter(
            is_active=True,
        ).select_related("domain").order_by("name")

        if domain_id:
            category_queryset = category_queryset.filter(domain_id=domain_id)
        else:
            category_queryset = category_queryset.none()

        self.fields["practice_category"].queryset = category_queryset
        self.fields["practice_category"].help_text = (
            "Only categories belonging to the selected practice domain are shown."
        )

    def clean(self):
        cleaned_data = super().clean()
        domain = cleaned_data.get("practice_domain")
        category = cleaned_data.get("practice_category")
        lesson_type = cleaned_data.get("lesson_type")

        if lesson_type == Lesson.TYPE_PRACTICE and domain and category:
            if category.domain_id != domain.id:
                self.add_error(
                    "practice_category",
                    "The selected category must belong to the selected practice domain.",
                )

        return cleaned_data
