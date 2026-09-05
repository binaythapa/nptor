from django import forms


class CVImportForm(forms.Form):
    source_file = forms.FileField(
        label="Existing CV",
        help_text="Upload a PDF or DOCX file (maximum 10 MB).",
    )
