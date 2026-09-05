from django import forms

from cv.models import CareerProfile, CV, CVTemplate


class CareerProfileForm(forms.ModelForm):
    class Meta:
        model = CareerProfile
        fields = (
            "professional_title",
            "summary",
            "linkedin_url",
            "portfolio_url",
        )
        widgets = {"summary": forms.Textarea(attrs={"rows": 6})}


class CVForm(forms.ModelForm):
    class Meta:
        model = CV
        fields = ("title", "template", "status", "overrides")
        widgets = {"overrides": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop("owner", None)
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = CVTemplate.objects.filter(is_active=True)
        self.fields["template"].required = False
        self.fields["status"].required = False
        if not self.instance.pk:
            self.fields["template"].initial = CVTemplate.objects.filter(is_active=True).first()
            self.fields["status"].initial = CV.STATUS_DRAFT
        self.owner = owner

    def clean_status(self):
        return self.cleaned_data.get("status") or CV.STATUS_DRAFT
