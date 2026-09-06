from django.test import SimpleTestCase
from django.template.loader import render_to_string


class CVTemplateRenderingFixTests(SimpleTestCase):
    def test_selected_template_slug_is_rendered(self):
        for slug in ("academic", "ats_classic", "executive", "fresher", "government", "minimal", "modern_professional", "technical"):
            context = {"cv": type("CV", (), {"title": "Test CV"})(), "payload": {"template": {"slug": slug}, "contact": {"first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com"}, "professional_title": "Product Designer"}, "config": {}}
            html = render_to_string(f"cv/render/{slug}.html", context)
            self.assertIn(f'data-cv-template="{slug}"', html)
