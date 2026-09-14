from pathlib import Path

from django.test import SimpleTestCase


class StudentProfileTemplateStyleTests(SimpleTestCase):
    def test_profile_template_uses_bulma_native_markup_and_page_styles(self):
        template_path = Path(__file__).resolve().parents[2] / "templates" / "organizations" / "student" / "profile.html"
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("{% load static %}", template)
        self.assertIn("student-profile.css", template)
        self.assertIn('class="student-profile-page"', template)
        self.assertIn('class="columns is-multiline"', template)
        self.assertIn('class="column is-half"', template)
        self.assertIn('class="student-profile-card"', template)
        self.assertNotIn("col-md-", template)
        self.assertNotIn("btn btn-", template)
        self.assertNotIn("d-flex", template)

    def test_profile_edit_template_uses_bulma_native_markup_and_page_styles(self):
        template_path = Path(__file__).resolve().parents[2] / "templates" / "organizations" / "student" / "profile_edit.html"
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("{% load static %}", template)
        self.assertIn("student-profile.css", template)
        self.assertIn('class="student-profile-page"', template)
        self.assertIn('class="student-profile-form"', template)
        self.assertIn('class="button is-primary"', template)
        self.assertNotIn("btn btn-", template)
        self.assertNotIn("card-body", template)
