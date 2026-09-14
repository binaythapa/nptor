from django import forms

from organizations.models import AcademicYear, ClassSection, StudentEnrollment


class StudentEnrollmentForm(forms.Form):
    academic_year = forms.ModelChoiceField(queryset=AcademicYear.objects.none(), label="Academic year")
    class_section = forms.ModelChoiceField(queryset=ClassSection.objects.none(), label="Class & section")
    roll_number = forms.CharField(max_length=50, required=False, label="Roll number")

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["academic_year"].queryset = AcademicYear.objects.filter(organization=organization).order_by("-start_date")
        self.fields["class_section"].queryset = ClassSection.objects.filter(organization=organization, is_active=True).select_related("academic_year", "class_group")
        self.fields["class_section"].label_from_instance = lambda obj: f"{obj.class_group.name} - {obj.name} ({obj.academic_year.name})"
        for field in self.fields.values():
            field.widget.attrs["class"] = "input"

    def clean(self):
        cleaned = super().clean()
        year = cleaned.get("academic_year")
        section = cleaned.get("class_section")
        if year and section and section.academic_year_id != year.id:
            self.add_error("class_section", "The selected section belongs to a different academic year.")
        return cleaned


class StudentEnrollmentUpdateForm(forms.ModelForm):
    class Meta:
        model = StudentEnrollment
        fields = ["roll_number", "status"]
        widgets = {"roll_number": forms.TextInput(attrs={"class": "input"}), "status": forms.Select(attrs={"class": "bulma-select"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [choice for choice in StudentEnrollment.STATUS_CHOICES if choice[0] != StudentEnrollment.STATUS_TRANSFERRED]


class StudentEnrollmentTransferForm(forms.Form):
    class_section = forms.ModelChoiceField(queryset=ClassSection.objects.none(), label="New class & section")
    roll_number = forms.CharField(max_length=50, required=False, label="New roll number")

    def __init__(self, *args, organization=None, academic_year=None, current_section=None, initial_roll_number="", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_section"].queryset = ClassSection.objects.filter(organization=organization, academic_year=academic_year, is_active=True).exclude(id=getattr(current_section, "id", None)).select_related("class_group")
        self.fields["class_section"].label_from_instance = lambda obj: f"{obj.class_group.name} - {obj.name} ({obj.academic_year.name})"
        self.fields["roll_number"].initial = initial_roll_number
        self.fields["class_section"].widget.attrs["class"] = "input"
        self.fields["roll_number"].widget.attrs["class"] = "input"
