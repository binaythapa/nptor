from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cv.models import CareerProfile, CVTemplate, DocumentArtifact
from cv.models_cv import CV
from cv.services.cv_builder import create_cv_version
from cv.services.delivery.base import DeliveryNotConfigured
from cv.services.delivery.email import EmailDeliveryProvider
from cv.services.delivery.whatsapp import WhatsAppDeliveryProvider


class DeliveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="delivery", email="delivery@example.com", password="pass")
        profile = CareerProfile.objects.create(user=self.user)
        template = CVTemplate.objects.create(name="Test", slug="delivery-test", is_active=True)
        self.cv = CV.objects.create(owner=self.user, profile=profile, template=template, title="Delivery CV")
        self.version = create_cv_version(self.cv)
        self.artifact = DocumentArtifact.objects.create(
            cv_version=self.version,
            artifact_type=DocumentArtifact.PDF,
            file=SimpleUploadedFile("delivery.pdf", b"pdf-bytes", content_type="application/pdf"),
            mime_type="application/pdf",
            template_slug="delivery-test",
            template_config={},
        )

    def test_email_provider_uses_account_email(self):
        provider = EmailDeliveryProvider()
        with patch("cv.services.delivery.email.EmailMessage.send") as send:
            result = provider.send(self.artifact, "wrong@example.com")
        self.assertEqual(result.status, "failed")
        send.assert_not_called()

    def test_whatsapp_is_not_configured_by_default(self):
        provider = WhatsAppDeliveryProvider()
        with self.assertRaises(DeliveryNotConfigured):
            provider.send(self.artifact, "+919999999999")
