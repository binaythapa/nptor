from organizations.models import OrganizationPortalConfig, OrganizationPortfolioSection, OrganizationProfile
from courses.models import Course


class OrganizationPortalService:
    """Build a safe, published view of an organization's public portal."""

    @staticmethod
    def profile(organization):
        profile, _ = OrganizationProfile.objects.get_or_create(
            organization=organization,
            defaults={"display_name": organization.name},
        )
        return profile

    @staticmethod
    def config(organization):
        config, _ = OrganizationPortalConfig.objects.get_or_create(
            organization=organization,
            defaults={"primary_color": organization.primary_color or "", "hero_title": organization.name},
        )
        return config

    @classmethod
    def published(cls, organization):
        profile = cls.profile(organization)
        config = cls.config(organization)
        sections = OrganizationPortfolioSection.objects.filter(organization=organization, is_enabled=True)
        courses = Course.objects.filter(
            organization=organization,
            is_public=True,
            is_published=True,
        ).order_by("title")
        return {"organization": organization, "profile": profile, "config": config, "sections": sections, "courses": courses}

    @classmethod
    def is_published(cls, organization):
        return organization.is_active and cls.config(organization).is_published
