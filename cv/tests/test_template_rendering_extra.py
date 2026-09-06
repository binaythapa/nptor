from django.test import SimpleTestCase
from django.template.loader import render_to_string


class CVTemplateRenderingExtraTests(SimpleTestCase):
    def test_government_template_is_distinct_from_base(self):
        context = {"cv": type("CV", (), {"title": "Test CV"})(), "payload": {"contact": {"first_name": "Alex", "last_name": "Morgan", "email": "alex@example.com"}, "professional_title": "Product Designer"}, "config": {}}
        html = render_to_string("cv/render/government.html", context)
        self.assertIn("template-government", html)
        self.assertIn("text-transform:uppercase", html)
