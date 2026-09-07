from django.test import SimpleTestCase
from django.template.loader import render_to_string


class CVTemplateRenderingAdditionalTests(SimpleTestCase):
    def test_template_slug_is_exposed_and_rendered_variants_differ(self):
        variants = ["academic", "ats_classic", "executive", "fresher", "government", "minimal", "modern_professional", "technical"]
        base_context = {"cv": type("CV", (), {"title": "Test CV"})(), "payload": {"template": {"slug": ""}, "contact": {"first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com"}, "professional_title": "Product Designer"}, "config": {}}
        rendered = {}
        for slug in variants:
            base_context["payload"]["template"]["slug"] = slug
            rendered[slug] = render_to_string(f"cv/render/{slug}.html", base_context)
        self.assertEqual(len(set(rendered.values())), len(variants))
        for slug in variants:
            self.assertIn(f'data-cv-template="{slug}"', rendered[slug])
