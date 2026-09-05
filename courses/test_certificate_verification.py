from pathlib import Path

from django.test import SimpleTestCase


class CertificateVerificationTemplateContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "certificate_verification.html"
        ).read_text(encoding="utf-8")

    def test_verification_hierarchy_exists(self):
        for hook in (
            'class="certificate-verification-page"',
            'class="certificate-status"',
            'class="certificate-details"',
            'class="certificate-completion"',
            'class="certificate-actions"',
        ):
            self.assertIn(hook, self.template)

    def test_verification_data_fields_are_preserved(self):
        for hook in (
            "certificate.certificate_id",
            "certificate.user",
            "certificate.course",
            "certificate.issued_at",
        ):
            self.assertIn(hook, self.template)

    def test_public_verification_route_is_named(self):
        from django.urls import reverse

        self.assertEqual(
            reverse("courses:certificate_verify", args=["CERT-TEST"]),
            "/courses/certificate/CERT-TEST/",
        )

    def test_verification_has_status_metadata_and_actions(self):
        for hook in (
            "Verified Certificate",
            "Officially issued by NPTOR",
            "Student",
            "Course",
            "Certificate ID",
            "Issued on",
            "Course Completion",
            "Download Certificate",
            "Share on LinkedIn",
            "Share on WhatsApp",
            "certificate_id",
        ):
            self.assertIn(hook, self.template)
