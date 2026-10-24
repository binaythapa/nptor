from django import forms
from django.utils.text import slugify

from vendors.models import VendorBankDetails, VendorProfile


class VendorOnboardingForm(forms.ModelForm):
    # Banking details collected alongside store application
    bank_name = forms.CharField(
        max_length=100,
        label="Bank Name",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Nabil Bank Ltd"}),
    )
    bank_account_name = forms.CharField(
        max_length=150,
        label="Account Holder Name",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Registered name on bank account"}),
    )
    bank_account_number = forms.CharField(
        max_length=50,
        label="Bank Account Number",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Account number"}),
    )
    bank_branch = forms.CharField(
        max_length=100,
        required=False,
        label="Branch",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Branch location (optional)"}),
    )

    class Meta:
        model = VendorProfile
        fields = [
            "store_name",
            "business_email",
            "business_phone",
            "pan_vat_number",
            "business_registration_number",
            "is_cod_enabled",
        ]
        widgets = {
            "store_name": forms.TextInput(attrs={"class": "input", "placeholder": "Store or brand name"}),
            "business_email": forms.EmailInput(attrs={"class": "input", "placeholder": "contact@yourstore.com"}),
            "business_phone": forms.TextInput(attrs={"class": "input", "placeholder": "+977-98XXXXXXXX"}),
            "pan_vat_number": forms.TextInput(attrs={"class": "input", "placeholder": "PAN or VAT number"}),
            "business_registration_number": forms.TextInput(attrs={"class": "input", "placeholder": "Registration number"}),
            "is_cod_enabled": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def clean_store_name(self):
        store_name = self.cleaned_data.get("store_name", "").strip()
        if not store_name:
            raise forms.ValidationError("Store name is required.")
        slug = slugify(store_name)
        if VendorProfile.objects.filter(slug=slug).exists():
            raise forms.ValidationError("A store with this name already exists. Please choose another.")
        return store_name

    def save(self, user, commit=True):
        profile = super().save(commit=False)
        profile.user = user
        profile.slug = slugify(profile.store_name)
        profile.status = VendorProfile.STATUS_PENDING
        if commit:
            profile.save()
            VendorBankDetails.objects.create(
                vendor=profile,
                bank_name=self.cleaned_data["bank_name"],
                bank_account_name=self.cleaned_data["bank_account_name"],
                bank_account_number=self.cleaned_data["bank_account_number"],
                bank_branch=self.cleaned_data.get("bank_branch", ""),
            )
        return profile
