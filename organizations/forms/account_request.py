from django import forms

from organizations.models.organization import Organization


class OrganizationAccountRequestForm(forms.Form):
    organization_name = forms.CharField(
        max_length=255,
        label="Organization name",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Your organization name"}),
    )
    org_type = forms.ChoiceField(
        choices=Organization.ORG_TYPE_CHOICES,
        label="Organization type",
        widget=forms.Select(attrs={"class": "select"}),
    )
    website = forms.URLField(
        required=False,
        label="Website",
        widget=forms.URLInput(attrs={"class": "input", "placeholder": "https://example.com"}),
    )
    contact_email = forms.EmailField(
        label="Contact email",
        widget=forms.EmailInput(attrs={"class": "input"}),
    )
    contact_phone = forms.CharField(
        required=False,
        max_length=50,
        label="Contact phone",
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    address = forms.CharField(
        required=False,
        label="Address",
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 2}),
    )
    city = forms.CharField(
        required=False,
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    country = forms.CharField(
        required=False,
        max_length=100,
        label="Country",
        initial="Nepal",
        widget=forms.TextInput(attrs={"class": "input"}),
    )
    description = forms.CharField(
        required=False,
        label="Organization description",
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 3}),
    )
    reason = forms.CharField(
        required=False,
        label="Why do you need an organization account?",
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 3}),
    )
