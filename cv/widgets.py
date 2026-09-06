from django import forms


class RichTextWidget(forms.Textarea):
    """Accessible textarea enhanced into the CV builder's resume-safe editor."""

    template_name = "django/forms/widgets/textarea.html"

    def __init__(self, attrs=None):
        base_attrs = {
            "class": "cv-rich-text__input",
            "data-rich-text": "true",
            "data-rich-text-mode": "resume",
            "rows": 7,
            "spellcheck": "true",
        }
        if attrs:
            base_attrs.update(attrs)
        super().__init__(attrs=base_attrs)
