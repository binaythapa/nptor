from django.utils.http import url_has_allowed_host_and_scheme

from organizations.models import Organization
from organizations.models.domain import OrganizationDomain


def normalize_host(host):
    return (host or "").split(":", 1)[0].strip().lower().rstrip(".")


class TenantResolver:
    """Resolve an organization from an explicit slug or a verified host."""

    @staticmethod
    def by_slug(slug):
        if not slug:
            return None
        return (
            Organization.objects
            .filter(slug=slug, is_active=True)
            .select_related("profile", "portal_config")
            .first()
        )

    @staticmethod
    def by_host(host):
        normalized = normalize_host(host)
        if not normalized:
            return None
        domain = (
            OrganizationDomain.objects
            .filter(domain=normalized, is_verified=True, organization__is_active=True)
            .select_related("organization", "organization__profile", "organization__portal_config")
            .first()
        )
        return domain.organization if domain else None

    @classmethod
    def resolve(cls, slug=None, host=None):
        """Explicit slug wins; otherwise resolve only verified domains."""
        if slug:
            return cls.by_slug(slug)
        return cls.by_host(host)
