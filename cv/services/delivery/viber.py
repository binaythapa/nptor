from cv.models_delivery import DeliveryRecord
from cv.services.delivery.base import DeliveryNotConfigured, DeliveryProvider


class ViberDeliveryProvider(DeliveryProvider):
    channel = DeliveryRecord.CHANNEL_VIBER
    name = "viber"

    def send(self, artifact, recipient, metadata=None):
        raise DeliveryNotConfigured("Viber delivery provider is not configured.")
