from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import CareerProfile, CV, CVTemplate
from cv.services.cv_builder import create_cv_version
from cv.services.documents.docx import generate_docx
from cv.services.documents.pdf import generate_pdf
from cv.services.documents.renderer import get_render_config, get_template_snapshot


class DocumentGenerationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="document-user", email="document@example.com", password="password"
        )
        self.template = CVTemplate.objects.create(
            slug="ats-classic",
            name="ATS Classic",
            config={
                "font_name": "Times-Roman",
                "font_size": 11,
                "heading_size": 13,
                "margin": 54,
                "accent_color": "#1f2937",
                "layout": "single_column",
                "header_style": "left",
                "section_style": "uppercase_rule",
                "density": "comfortable",
            },
        )
        self.profile = CareerProfile.objects.create(
            user=self.user,
            professional_title="Senior Data Engineer",
            summary="Builds reliable data platforms.",
        )
        self.cv = CV.objects.create(
            owner=self.user,
            profile=self.profile,
            template=self.template,
            title="Software Engineer CV",
        )
        self.version = create_cv_version(self.cv)

    def test_pdf_generation_returns_pdf_artifact(self):
        artifact = generate_pdf(self.version)
        self.assertEqual(artifact.mime_type, "application/pdf")
        self.assertGreater(artifact.file.size, 0)
        artifact.file.seek(0)
        self.assertTrue(artifact.file.read(5).startswith(b"%PDF"))

    def test_docx_generation_returns_docx_artifact(self):
        artifact = generate_docx(self.version)
        self.assertEqual(
            artifact.mime_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertGreater(artifact.file.size, 0)
        artifact.file.seek(0)
        self.assertEqual(artifact.file.read(2), b"PK")

    def test_template_snapshot_is_frozen_in_version(self):
        self.assertEqual(get_template_snapshot(self.template), self.version.snapshot["template"])
        self.template.config = {"font_size": 20}
        self.template.save(update_fields=["config"])
        self.assertEqual(self.version.snapshot["template"]["config"]["font_size"], 11)

    def test_render_config_normalizes_template_style_settings(self):
        config = get_render_config(self.version.snapshot["template"])
        self.assertEqual(config["font_name"], "Times-Roman")
        self.assertEqual(config["font_size"], 11)
        self.assertEqual(config["heading_size"], 13)
        self.assertEqual(config["margin"], 54)
        self.assertEqual(config["accent_color"], "#1f2937")
        self.assertEqual(config["layout"], "single_column")
        self.assertEqual(config["header_style"], "left")
        self.assertEqual(config["section_style"], "uppercase_rule")
        self.assertEqual(config["density"], "comfortable")

    def test_render_config_rejects_unsafe_style_values(self):
        template = {
            "config": {
                "font_name": "Comic Sans",
                "font_size": 99,
                "heading_size": 1,
                "margin": 500,
                "accent_color": "not-a-color",
                "layout": "javascript",
                "header_style": "script",
                "section_style": "unknown",
                "density": "huge",
            }
        }
        config = get_render_config(template)
        self.assertEqual(config["font_name"], "Helvetica")
        self.assertEqual(config["font_size"], 10)
        self.assertEqual(config["heading_size"], 12)
        self.assertEqual(config["margin"], 48)
        self.assertEqual(config["accent_color"], "#111827")
        self.assertEqual(config["layout"], "single_column")
        self.assertEqual(config["header_style"], "left")
        self.assertEqual(config["section_style"], "uppercase_rule")
        self.assertEqual(config["density"], "comfortable")

    def test_template_styles_are_normalized_for_renderers(self):
        config = get_render_config(
            {
                "config": {
                    "layout": "sidebar",
                    "header_style": "centered",
                    "section_style": "minimal",
                    "density": "compact",
                }
            }
        )
        self.assertEqual(config["layout"], "sidebar")
        self.assertEqual(config["header_style"], "centered")
        self.assertEqual(config["section_style"], "minimal")
        self.assertEqual(config["density"], "compact")
