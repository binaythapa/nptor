import secrets

import dns.resolver
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
        if is_primary and domain_type == OrganizationDomain.DOMAIN_TYPE_CUSTOM:
            is_primary = False
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
    def verification_name(record):
        return f"_nptor-verification.{record.domain}"

    @classmethod
    def verify(cls, record):
        if record.domain_type == OrganizationDomain.DOMAIN_TYPE_CUSTOM:
            try:
                answers = dns.resolver.resolve(cls.verification_name(record), "TXT")
                values = {str(value).strip('"') for answer in answers for value in answer.strings}
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
                raise ValidationError(
                    f"DNS verification failed. Add a TXT record at {cls.verification_name(record)} with the provided verification token."
                ) from exc
            if record.verification_token not in values:
                raise ValidationError("The DNS TXT record does not contain the expected verification token.")

        record.is_verified = True
        record.ssl_status = OrganizationDomain.SSL_PENDING
        record.save(update_fields=["is_verified", "ssl_status"])
        return record

    @staticmethod
    def set_primary(record):
        if not record.is_verified:
            raise ValidationError("Only verified domains can be primary.")
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
