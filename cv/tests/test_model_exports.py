from django.test import SimpleTestCase
from django.urls import reverse

from cv.models import CVImport, DocumentArtifact, ImportedField


class CVModelExportTests(SimpleTestCase):
    def test_split_models_are_available_from_cv_models(self):
        self.assertTrue(CVImport)
        self.assertTrue(ImportedField)
        self.assertTrue(DocumentArtifact)

    def test_export_routes_are_registered(self):
        self.assertEqual(reverse("cv:cv_export_pdf", kwargs={"pk": 1}), "/cv/1/export/pdf/")
        self.assertEqual(reverse("cv:cv_export_docx", kwargs={"pk": 1}), "/cv/1/export/docx/")
