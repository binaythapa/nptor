from django import forms
from django.test import SimpleTestCase

from cv.forms import (
    CareerAchievementForm,
    CareerEducationForm,
    CareerExperienceForm,
    CareerProfileForm,
    CareerProjectForm,
)


class CareerRichTextEditorTests(SimpleTestCase):
    def test_rich_text_fields_use_rich_text_widget(self):
        for form_class, field_name in (
            (CareerProfileForm, "summary"),
            (CareerExperienceForm, "description"),
            (CareerEducationForm, "description"),
            (CareerProjectForm, "description"),
            (CareerAchievementForm, "description"),
        ):
            with self.subTest(form=form_class.__name__):
                field = form_class().fields[field_name]
                self.assertEqual(field.widget.__class__.__name__, "RichTextWidget")

    def test_rich_text_widget_is_still_a_textarea(self):
        widget = CareerProjectForm().fields["description"].widget
        self.assertIsInstance(widget, forms.Textarea)
        self.assertEqual(widget.attrs["data-rich-text"], "true")

    def test_structured_fields_do_not_use_rich_text_editor(self):
        form = CareerProjectForm()
        self.assertNotIn("data-rich-text", form.fields["name"].widget.attrs)
        self.assertNotIn("data-rich-text", form.fields["role"].widget.attrs)
        self.assertNotIn("data-rich-text", form.fields["technologies"].widget.attrs)
