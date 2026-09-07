from django.db.models.signals import post_save
from django.dispatch import receiver

from organizations.models.organization import Organization
from organizations.models.portal import OrganizationPortalConfig
from organizations.models.profile import OrganizationProfile


@receiver(post_save, sender=Organization)
def create_organization_portal_defaults(sender, instance, created, **kwargs):
    """Keep the new tenant portal records present for every organization."""
    if not created:
        return

    OrganizationProfile.objects.get_or_create(
        organization=instance,
        defaults={
            "display_name": instance.name,
            "logo": instance.logo.name if instance.logo else None,
        },
    )
    OrganizationPortalConfig.objects.get_or_create(
        organization=instance,
        defaults={
            "primary_color": instance.primary_color or "",
            "hero_title": instance.name,
            "is_published": False,
        },
    )
