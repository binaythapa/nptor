from django import forms

from cv.models import CareerProfile


class CareerProfileForm(forms.ModelForm):
    class Meta:
        model = CareerProfile
        fields = [
            "professional_title",
            "summary",
            "linkedin_url",
            "portfolio_url",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 6}),
        }
