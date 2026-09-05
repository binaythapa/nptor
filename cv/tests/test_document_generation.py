from io import BytesIO

from django.core.files.base import ContentFile
from django.test import TestCase
from django.contrib.auth import get_user_model

from cv.models import CV, CVTemplate
from cv.models_version import CVVersion
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
        self.cv = CV.objects.create(
            owner=self.user,
            profile=self.user.career_profile if hasattr(self.user, "career_profile") else None,
            template=self.template,
            title="Software Engineer CV",
        )
        if self.cv.profile_id is None:
            from cv.models import CareerProfile
            self.cv.profile = CareerProfile.objects.create(user=self.user)
            self.cv.save(update_fields=["profile"])
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
