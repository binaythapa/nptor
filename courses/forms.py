from django import forms
from django.forms import inlineformset_factory

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Course, CourseSection, Lesson


# =====================================================
# COURSE FORM
# =====================================================

class CourseForm(forms.ModelForm):

    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "textarea"
            }
        )
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
            "is_public",
            "is_published",
        ]

        widgets = {
            "subscription_plans": forms.CheckboxSelectMultiple(),
        }


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