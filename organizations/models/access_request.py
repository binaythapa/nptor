from django.conf import settings
from django.db import models

from .organization import Organization
from .role import OrganizationRole


class OrganizationAccessRequest(models.Model):
    """A user's request for an organization service/access role."""

    SERVICE_ORGANIZATION_ACCESS = "ORGANIZATION_ACCESS"
    SERVICE_CHOICES = (
        (SERVICE_ORGANIZATION_ACCESS, "Organization access"),
    )

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_REVOKED = "REVOKED"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_REVOKED, "Revoked"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_access_requests")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="access_requests")
    service = models.CharField(max_length=40, choices=SERVICE_CHOICES, default=SERVICE_ORGANIZATION_ACCESS)
    requested_role = models.CharField(max_length=20, choices=OrganizationRole.choices, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="reviewed_organization_access_requests")
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="org_access_req_org_status_idx"),
            models.Index(fields=["user", "status"], name="org_access_req_user_status_idx"),
            models.Index(fields=["service", "status"], name="org_access_req_service_idx"),
        ]

    def __str__(self):
        return f"{self.user} → {self.organization} ({self.status})"
