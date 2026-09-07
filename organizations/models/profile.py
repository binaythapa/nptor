from django.db import models

from .organization import Organization


class OrganizationProfile(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=255, blank=True)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="org/profiles/logos/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="org/profiles/covers/", blank=True, null=True)
    favicon = models.ImageField(upload_to="org/profiles/favicons/", blank=True, null=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.organization.name
