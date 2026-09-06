from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase


class CVImportViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="cv-import-view-user",
            password="password",
        )
        self.client.force_login(self.user)

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
