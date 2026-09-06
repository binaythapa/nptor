from django.test import TestCase

from cv.models import CVTemplate
from cv.services.documents.renderer import get_render_config


class CVTemplateConfigurationTests(TestCase):
    def test_seeded_templates_have_distinct_presentation_configurations(self):
        templates = {template.slug: template for template in CVTemplate.objects.filter(is_active=True)}
        expected = {"academic", "ats-classic", "executive", "fresher", "government", "minimal", "modern-professional", "technical"}
        self.assertTrue(expected.issubset(templates))
        configs = {slug: tuple(sorted(get_render_config(template.config).items())) for slug, template in templates.items() if slug in expected}
        self.assertEqual(len(configs), len(expected))
        self.assertGreaterEqual(len(set(configs.values())), 5)

    def test_modern_and_technical_templates_use_sidebar_layout(self):
        for slug in ("modern-professional", "technical"):
            template = CVTemplate.objects.get(slug=slug)
            self.assertEqual(get_render_config(template.config)["layout"], "sidebar")
