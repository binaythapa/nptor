from django import forms
from django.forms import inlineformset_factory

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Course, CourseSection, Lesson
from quiz.models import Category, Domain

class CourseForm(forms.ModelForm):

    description = forms.CharField(
        widget=CKEditorUploadingWidget(
            config_name="default"
        ),
        required=False
    )

    class Meta:
        model = Course

        fields = [
            "title",
            "description",
            "domain",
            "category",
            "thumbnail",
            "level",
            "subscription_plans",
            "is_public",
            "is_published",
        ]

        widgets = {
            "subscription_plans": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create Course page
        self.fields["category"].queryset = Category.objects.none()

        if "domain" in self.data:

            try:
                domain_id = int(self.data.get("domain"))

                self.fields["category"].queryset = (
                    Category.objects.filter(
                        domain_id=domain_id,
                        is_active=True
                    ).order_by("name")
                )

            except (ValueError, TypeError):
                pass

        # Edit Course page
        elif self.instance.pk and self.instance.domain:

            self.fields["category"].queryset = (
                Category.objects.filter(
                    domain=self.instance.domain,
                    is_active=True
                ).order_by("name")
            )
# =====================================================
# COURSE SECTION FORMSET
# =====================================================

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


# =====================================================
# LESSON FORM
# =====================================================

class LessonForm(forms.ModelForm):

    article_content = forms.CharField(
        widget=CKEditorUploadingWidget(
            config_name="default"
        ),
        required=False,
        label="Lesson Content"
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