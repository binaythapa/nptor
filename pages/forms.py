from django import forms
from .models import Testimonial


class TestimonialForm(forms.ModelForm):

    class Meta:
        model = Testimonial
        fields = [
            "message",
            "rating",
            "exam_track",
            "course",
            "study_plan",
        ]

        widgets = {
            "message": forms.Textarea(attrs={
                "class": "textarea",
                "rows": 4,
                "placeholder": "Share your experience..."
            }),
            "rating": forms.Select(attrs={
                "class": "input"
            }),
        }