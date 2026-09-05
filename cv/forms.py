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


class CVBuilderForm(forms.Form):
    """CV-specific presentation fields; master career profile stays unchanged."""

    title = forms.CharField(max_length=255)
    template = forms.ModelChoiceField(queryset=CVTemplate.objects.none())
    status = forms.ChoiceField(choices=CV.STATUS_CHOICES)
    professional_title = forms.CharField(max_length=255, required=False)
    summary = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    linkedin_url = forms.URLField(required=False)
    portfolio_url = forms.URLField(required=False)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = CVTemplate.objects.filter(is_active=True)
        if instance is not None:
            overrides = instance.overrides or {}
            self.initial.update(
                {
                    "title": instance.title,
                    "template": instance.template_id,
                    "status": instance.status,
                    "professional_title": overrides.get("professional_title", instance.profile.professional_title),
                    "summary": overrides.get("summary", instance.profile.summary),
                    "linkedin_url": overrides.get("linkedin_url", instance.profile.linkedin_url),
                    "portfolio_url": overrides.get("portfolio_url", instance.profile.portfolio_url),
                }
            )
