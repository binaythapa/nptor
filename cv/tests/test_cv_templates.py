from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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

    def test_seeded_templates_have_distinct_rendering_styles(self):
        call_command("seed_cv_templates")
        configs = dict(CVTemplate.objects.values_list("slug", "config"))

        self.assertEqual(configs["ats-classic"]["layout"], "single_column")
        self.assertEqual(configs["modern-professional"]["layout"], "sidebar")
        self.assertEqual(configs["executive"]["header_style"], "centered")
        self.assertEqual(configs["technical"]["section_style"], "minimal")
        self.assertEqual(configs["fresher"]["density"], "comfortable")
        self.assertEqual(configs["academic"]["font_name"], "Times-Roman")
        self.assertEqual(configs["government"]["section_style"], "title_case")
        self.assertEqual(configs["minimal"]["density"], "compact")

    def test_template_gallery_exposes_a_use_link_for_each_active_template(self):
        user = get_user_model().objects.create_user(username="template-gallery", password="password")
        call_command("seed_cv_templates")
        self.client.force_login(user)

        response = self.client.get(reverse("cv:cv_templates"))

        self.assertEqual(response.status_code, 200)
        for slug in EXPECTED_TEMPLATES:
            self.assertContains(response, f"?template={slug}")

    def test_create_page_honors_template_selected_from_gallery(self):
        user = get_user_model().objects.create_user(username="template-create", password="password")
        call_command("seed_cv_templates")
        selected = CVTemplate.objects.get(slug="technical")
        self.client.force_login(user)

        response = self.client.get(reverse("cv:cv_create") + "?template=technical")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["template"], selected)
