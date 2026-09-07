from django.db import models, router, transaction
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower

from .organization import Organization


class OrganizationDomain(models.Model):
    DOMAIN_TYPE_SUBDOMAIN = "nptor_subdomain"
    DOMAIN_TYPE_CUSTOM = "custom"
    DOMAIN_TYPE_CHOICES = (
        (DOMAIN_TYPE_SUBDOMAIN, "NPTOR Subdomain"),
        (DOMAIN_TYPE_CUSTOM, "Custom Domain"),
    )

    SSL_PENDING = "pending"
    SSL_ACTIVE = "active"
    SSL_ERROR = "error"
    SSL_STATUS_CHOICES = (
        (SSL_PENDING, "Pending"),
        (SSL_ACTIVE, "Active"),
        (SSL_ERROR, "Error"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="organization_domains",
    )
    domain = models.CharField(max_length=255)
    domain_type = models.CharField(max_length=30, choices=DOMAIN_TYPE_CHOICES, default=DOMAIN_TYPE_CUSTOM)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=128, blank=True)
    ssl_status = models.CharField(max_length=20, choices=SSL_STATUS_CHOICES, default=SSL_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "domain"]
        constraints = [
            models.UniqueConstraint(Lower("domain"), name="org_domain_ci_unique"),
        ]
        indexes = [models.Index(fields=["organization", "is_verified"], name="org_domain_verified_idx")]

    def save(self, *args, **kwargs):
        self.domain = self.domain.strip().lower().rstrip(".")
        if not self.is_primary:
            return super().save(*args, **kwargs)

        using = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        with transaction.atomic(using=using):
            Organization.objects.using(using).select_for_update().get(pk=self.organization_id)
            existing = type(self).objects.using(using).filter(
                organization_id=self.organization_id,
                is_primary=True,
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("An organization can have only one primary domain.")
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.domain
