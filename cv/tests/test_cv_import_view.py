from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cv.models_import import CVImport


class CVImportViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cv-import-view-user",
            password="password",
        )
        self.client.force_login(self.user)

    def test_import_page_uses_multipart_file_input_for_supported_formats(self):
        response = self.client.get("/cv/import/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"')

    def test_import_view_redirects_to_review_after_successful_pdf_upload(self):
        upload = self._pdf_upload("John Doe", "john@example.com")

        response = self.client.post("/cv/import/", {"source_file": upload})

        imported = CVImport.objects.get(owner=self.user)
        self.assertRedirects(response, f"/cv/import/{imported.pk}/review/")
        self.assertEqual(imported.status, CVImport.STATUS_REVIEW)
        self.assertEqual(imported.original_filename, "resume.pdf")

    def test_import_view_shows_upload_error_for_unparseable_pdf(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-this-is-not-a-valid-pdf",
            content_type="application/pdf",
        )

        response = self.client.post("/cv/import/", {"source_file": upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not read the uploaded CV")
        self.assertContains(response, "source_file")
        self.assertFalse(CVImport.objects.filter(owner=self.user).exists())

    def _pdf_upload(self, name, email):
        from reportlab.pdfgen import canvas

        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        pdf.drawString(72, 720, name)
        pdf.drawString(72, 700, email)
        pdf.save()
        stream.seek(0)
        return SimpleUploadedFile("resume.pdf", stream.read(), content_type="application/pdf")
