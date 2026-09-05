from cv.models_delivery import DeliveryRecord
from cv.services.delivery.base import DeliveryNotConfigured, DeliveryProvider


class WhatsAppDeliveryProvider(DeliveryProvider):
    channel = DeliveryRecord.CHANNEL_WHATSAPP
    name = "whatsapp"

    def send(self, artifact, recipient, metadata=None):
        raise DeliveryNotConfigured("WhatsApp delivery provider is not configured.")
