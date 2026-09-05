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
        self.assertEqual(
            reverse("courses:certificate_download", args=["CERT-TEST"]),
            "/courses/certificate/CERT-TEST/download/",
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

    def test_verification_view_is_public_and_certificate_scoped(self):
        source = (
            Path(__file__).resolve().parent / "views" / "certificate.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def certificate_verify(request, certificate_id):", source)
        self.assertIn("get_object_or_404(", source)
        self.assertIn("certificate_id=certificate_id", source)
        self.assertIn("def certificate_download(request, certificate_id):", source)


class CoursePlayerCertificateLinkContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_player.html"
        ).read_text(encoding="utf-8")

    def test_completed_course_card_exposes_public_verification_link(self):
        self.assertIn("certificate.certificate_id", self.template)
        self.assertIn("courses:certificate_verify", self.template)
        self.assertIn("View & Verify Certificate", self.template)
