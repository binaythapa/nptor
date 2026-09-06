from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.forms import CVForm
from cv.models_template import CVTemplate
from cv.services.documents.renderer import get_render_config


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

        response = self.client.get("/cv/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cv-template-search")
        self.assertContains(response, "cv-template-filters")
        self.assertContains(response, "data-template-category=\"Modern\"")
        self.assertContains(response, "ATS-friendly")
        self.assertContains(response, "Best for")
        self.assertContains(response, "data-template-ats=\"true\"")

    def test_render_config_selects_reference_inspired_design_styles(self):
        modern = get_render_config({"config": {"layout": "single_column", "header_style": "left"}})
        split = get_render_config({"config": {"layout": "sidebar"}})
        elegant = get_render_config({"config": {"header_style": "centered"}})

        self.assertEqual(modern["design_style"], "modern_header")
        self.assertEqual(split["design_style"], "split_label")
        self.assertEqual(elegant["design_style"], "elegant")

    def test_render_config_accepts_explicit_design_style(self):
        config = get_render_config({"config": {"design_style": "elegant", "layout": "single_column"}})
        self.assertEqual(config["design_style"], "elegant")

    def test_template_gallery_marks_each_preview_with_renderer_design_style(self):
        user = get_user_model().objects.create_user(
            username="cv-design-gallery-user",
            password="test-password",
        )
        self.client.force_login(user)
        CVTemplate.objects.create(
            slug="gallery-modern",
            name="Gallery Modern",
            description="Modern reference design",
            config={"design_style": "modern_header", "layout": "single_column"},
            is_active=True,
        )
        CVTemplate.objects.create(
            slug="gallery-split",
            name="Gallery Split",
            description="Split reference design",
            config={"design_style": "split_label", "layout": "single_column"},
            is_active=True,
        )
        CVTemplate.objects.create(
            slug="gallery-elegant",
            name="Gallery Elegant",
            description="Elegant reference design",
            config={"design_style": "elegant", "layout": "single_column"},
            is_active=True,
        )

        response = self.client.get("/cv/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cv-mini-paper--modern-header")
        self.assertContains(response, "cv-mini-paper--split-label")
        self.assertContains(response, "cv-mini-paper--elegant")
        self.assertContains(response, "data-template-design=\"modern_header\"")
        self.assertContains(response, "data-template-design=\"split_label\"")
        self.assertContains(response, "data-template-design=\"elegant\"")
        self.assertContains(response, "cv-mini-photo-placeholder")
        self.assertContains(response, "cv-mini-sidebar--left")
        self.assertContains(response, "cv-mini-sidebar-pattern")
        self.assertContains(response, "cv-mini-contact-list")
