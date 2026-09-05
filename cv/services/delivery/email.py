from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from cv.models_delivery import DeliveryRecord
from cv.services.delivery.base import DeliveryNotConfigured, DeliveryProvider, DeliveryResult


class EmailDeliveryProvider(DeliveryProvider):
    channel = DeliveryRecord.CHANNEL_EMAIL
    name = "django-email"

    def send(self, artifact, recipient, metadata=None):
        owner = artifact.cv_version.cv.owner
        authoritative_email = (owner.email or "").strip().lower()
        if not authoritative_email or recipient.strip().lower() != authoritative_email:
            return DeliveryResult(DeliveryRecord.STATUS_FAILED, self.name, "Recipient must match the account email.")
        if not getattr(settings, "EMAIL_HOST_USER", ""):
            raise DeliveryNotConfigured("Email delivery is not configured.")
        record = DeliveryRecord.objects.create(
            owner=owner,
            artifact=artifact,
            channel=self.channel,
            document_format=artifact.artifact_type,
            recipient=authoritative_email,
            provider=self.name,
            metadata=metadata or {},
        )
        try:
            email = EmailMessage(
                subject=f"Your NPTOR CV - {artifact.cv_version.cv.title}",
                body="Your requested CV is attached.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[authoritative_email],
            )
            email.attach(artifact.file.name.rsplit("/", 1)[-1], artifact.file.read(), artifact.mime_type)
            email.send(fail_silently=False)
        except Exception as exc:
            record.status = DeliveryRecord.STATUS_FAILED
            record.error_message = str(exc)[:2000]
            record.save(update_fields=["status", "error_message"])
            return DeliveryResult(DeliveryRecord.STATUS_FAILED, self.name, record.error_message)
        record.status = DeliveryRecord.STATUS_SENT
        record.sent_at = timezone.now()
        record.save(update_fields=["status", "sent_at"])
        return DeliveryResult(DeliveryRecord.STATUS_SENT, self.name)
