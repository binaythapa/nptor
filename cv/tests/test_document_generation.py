from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import CareerProfile, CV, CVTemplate
from cv.services.cv_builder import create_cv_version
from cv.services.documents.docx import generate_docx
from cv.services.documents.pdf import generate_pdf
from cv.services.documents.renderer import get_template_snapshot


class DocumentGenerationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="document-user", email="document@example.com", password="password"
        )
        self.template = CVTemplate.objects.create(
            slug="ats-classic", name="ATS Classic", config={"font_size": 11}
        )
        self.profile = CareerProfile.objects.create(user=self.user)
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
