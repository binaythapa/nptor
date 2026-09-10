from django import forms

from organizations.models import OrganizationStudent


class OrganizationStudentProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(disabled=True, required=False)

    class Meta:
        model = OrganizationStudent
        fields = ["first_name", "last_name", "email", "date_of_birth", "guardian_name", "guardian_phone", "address"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user.first_name = self.cleaned_data.get("first_name", "")
        instance.user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            instance.user.save(update_fields=["first_name", "last_name"])
            instance.save()
        return instance
