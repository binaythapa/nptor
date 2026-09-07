import secrets

from django.core.exceptions import ValidationError

from organizations.models import OrganizationDomain


class OrganizationDomainService:
    """Manage normalized, verified tenant domains."""

    @staticmethod
    def normalize(domain):
        value = (domain or "").strip().lower().rstrip(".")
        if not value or "/" in value or "@" in value or " " in value:
            raise ValidationError("Enter a valid hostname, not a URL or email address.")
        return value

    @classmethod
    def create(cls, organization, domain, domain_type=OrganizationDomain.DOMAIN_TYPE_CUSTOM, is_primary=False):
        normalized = cls.normalize(domain)
        if OrganizationDomain.objects.filter(domain__iexact=normalized).exists():
            raise ValidationError("This domain is already registered.")
        record = OrganizationDomain(
            organization=organization,
            domain=normalized,
            domain_type=domain_type,
            is_primary=is_primary,
            verification_token=secrets.token_urlsafe(32),
        )
        record.full_clean()
        record.save()
        return record

    @staticmethod
    def verify(record):
        record.is_verified = True
        record.ssl_status = OrganizationDomain.SSL_PENDING
        record.save(update_fields=["is_verified", "ssl_status"])
        return record

    @staticmethod
    def set_primary(record):
        OrganizationDomain.objects.filter(
            organization=record.organization,
            is_primary=True,
        ).exclude(pk=record.pk).update(is_primary=False)
        record.is_primary = True
        record.save(update_fields=["is_primary"])
        return record

    @staticmethod
    def active_for_host(host):
        normalized = (host or "").split(":", 1)[0].strip().lower().rstrip(".")
        return (
            OrganizationDomain.objects
            .filter(domain=normalized, is_verified=True, organization__is_active=True)
            .select_related("organization")
            .first()
        )
