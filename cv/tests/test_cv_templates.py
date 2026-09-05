from django.core.management import call_command
from django.test import TestCase

from cv.models_template import CVTemplate


EXPECTED_TEMPLATES = {
    "ats-classic": "ATS Classic",
    "modern-professional": "Modern Professional",
    "executive": "Executive",
    "technical": "Technical",
    "fresher": "Fresher",
    "academic": "Academic",
    "government": "Government",
    "minimal": "Minimal",
}


class CVTemplateTests(TestCase):
    def test_template_slugs_are_stable(self):
        template = CVTemplate.objects.create(
            slug="ats-classic",
            name="ATS Classic",
            config={"font": "Arial", "accent": "#111827"},
        )
        self.assertEqual(template.slug, "ats-classic")
        self.assertEqual(template.config["font"], "Arial")

    def test_template_configuration_is_independent_of_cv_content(self):
        template = CVTemplate.objects.create(
            slug="modern-professional",
            name="Modern Professional",
            config={"layout": "two-column"},
        )
        self.assertEqual(template.config["layout"], "two-column")

    def test_seed_command_creates_exactly_eight_default_templates(self):
        call_command("seed_cv_templates")
        templates = dict(CVTemplate.objects.values_list("slug", "name"))

        self.assertEqual(templates, EXPECTED_TEMPLATES)
        self.assertEqual(CVTemplate.objects.count(), 8)

    def test_seed_command_is_idempotent(self):
        call_command("seed_cv_templates")
        call_command("seed_cv_templates")

        self.assertEqual(CVTemplate.objects.count(), 8)
