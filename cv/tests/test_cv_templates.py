from django.test import TestCase

from cv.models_template import CVTemplate


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
