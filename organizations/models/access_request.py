from django.conf import settings
from django.db import models

from .organization import Organization
from .role import OrganizationRole


class OrganizationAccessRequest(models.Model):
    """A platform-admin reviewed request for organization access/services."""

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    SERVICE_ORGANIZATION_ACCESS = "organization_access"
    SERVICE_CHOICES = (
        (SERVICE_ORGANIZATION_ACCESS, "Organization Access"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_access_requests",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    requested_role = models.CharField(
        max_length=20,
        choices=OrganizationRole.choices,
        default=OrganizationRole.STUDENT,
    )
    reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_organization_access_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.organization} ({self.status})"
