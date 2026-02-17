from django import forms
from .models import *

class CourseForm(forms.ModelForm):

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
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "subscription_plans": forms.CheckboxSelectMultiple(),
        }




from django.forms import inlineformset_factory

CourseSectionFormSet = inlineformset_factory(
    Course,
    CourseSection,
    fields=("title", "order"),  # 👈 add order here
    extra=1,
    can_delete=True   # 🔥 ADD THIS
)


from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import Lesson

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
