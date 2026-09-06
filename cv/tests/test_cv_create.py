from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.forms import CVForm
from cv.models_template import CVTemplate


class CVCreateFormTests(TestCase):
    def test_create_form_hides_internal_overrides_field(self):
        form = CVForm()

        self.assertNotIn("overrides", form.fields)
        self.assertEqual(
            list(form.fields),
            ["title", "template", "status"],
        )

    def test_template_gallery_renders_real_resume_preview_content(self):
        user = get_user_model().objects.create_user(
            username="cv-preview-user",
            password="test-password",
        )
        self.client.force_login(user)
        CVTemplate.objects.create(
            slug="preview-sidebar",
            name="Preview Sidebar",
            description="Sidebar preview",
            config={
                "accent_color": "#0f766e",
                "layout": "sidebar",
                "header_style": "compact",
                "section_style": "minimal",
                "density": "compact",
            },
            is_active=True,
        )

        response = self.client.get("/cv/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Morgan")
        self.assertContains(response, "Product Designer")
        self.assertContains(response, "Professional Summary")
        self.assertContains(response, "Experience")
        self.assertContains(response, "Skills")
        self.assertContains(response, "cv-mini-paper--sidebar")
        self.assertContains(response, "cv-template-page-header")
        self.assertContains(response, "cv-template-page-heading")
        self.assertNotContains(response, "cv-paper__line")

    def test_template_gallery_exposes_discovery_metadata_and_filters(self):
        user = get_user_model().objects.create_user(
            username="cv-gallery-user",
            password="test-password",
        )
        self.client.force_login(user)
        CVTemplate.objects.create(
            slug="modern-professional",
            name="Modern Professional",
            description="Contemporary two-column layout.",
            config={
                "accent_color": "#2563eb",
                "layout": "sidebar",
                "header_style": "left",
                "section_style": "uppercase_rule",
                "density": "comfortable",
            },
            is_active=True,
        )

        response = self.client.get("/cv/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cv-template-search")
        self.assertContains(response, "cv-template-filters")
        self.assertContains(response, "data-template-category=\"Modern\"")
        self.assertContains(response, "ATS-friendly")
        self.assertContains(response, "Best for")
        self.assertContains(response, "data-template-ats=\"true\"")
