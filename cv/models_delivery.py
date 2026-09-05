from django.conf import settings
from django.db import models

from cv.models_document import DocumentArtifact


class DeliveryRecord(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_WHATSAPP = "whatsapp"
    CHANNEL_VIBER = "viber"
    CHANNEL_CHOICES = (
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_WHATSAPP, "WhatsApp"),
        (CHANNEL_VIBER, "Viber"),
    )
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_delivery_records")
    artifact = models.ForeignKey(DocumentArtifact, on_delete=models.CASCADE, related_name="deliveries")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    document_format = models.CharField(max_length=10)
    recipient = models.CharField(max_length=320)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    provider = models.CharField(max_length=60, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "channel", "status"], name="cv_delivery_owner_idx")]

    def __str__(self):
        return f"{self.channel}: {self.artifact}"
