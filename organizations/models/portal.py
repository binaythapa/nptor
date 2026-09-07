from django.db import models

from .organization import Organization


class OrganizationPortalConfig(models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="portal_config",
    )
    primary_color = models.CharField(max_length=20, blank=True)
    secondary_color = models.CharField(max_length=20, blank=True)
    hero_title = models.CharField(max_length=255, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_image = models.ImageField(upload_to="org/portals/hero/", blank=True, null=True)
    welcome_message = models.TextField(blank=True)
    show_courses = models.BooleanField(default=True)
    show_tracks = models.BooleanField(default=True)
    show_exams = models.BooleanField(default=True)
    show_about = models.BooleanField(default=True)
    show_testimonials = models.BooleanField(default=True)
    show_contact = models.BooleanField(default=True)
    custom_footer_text = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Portal config: {self.organization.name}"
