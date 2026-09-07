from django.test import SimpleTestCase
from django.template.loader import render_to_string


class CVTemplateRenderingNewTests(SimpleTestCase):
    def test_template_selection_is_visible_in_rendered_markup(self):
        slugs = ["academic", "ats_classic", "executive", "fresher", "government", "minimal", "modern_professional", "technical"]
        for slug in slugs:
            context = {"cv": type("CV", (), {"title": "Test CV"})(), "payload": {"template": {"slug": slug}, "contact": {"first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com"}, "professional_title": "Product Designer"}, "config": {}}
            html = render_to_string(f"cv/render/{slug}.html", context)
            self.assertIn(f'data-cv-template="{slug}"', html)
