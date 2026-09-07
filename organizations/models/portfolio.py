from django.db import models

from .organization import Organization


class OrganizationPortfolioSection(models.Model):
    HERO = "hero"
    ABOUT = "about"
    FEATURED_COURSES = "featured_courses"
    LEARNING_PROGRAMS = "learning_programs"
    ACHIEVEMENTS = "achievements"
    TESTIMONIALS = "testimonials"
    CONTACT = "contact"
    CUSTOM_TEXT = "custom_text"

    SECTION_CHOICES = (
        (HERO, "Hero"),
        (ABOUT, "About"),
        (FEATURED_COURSES, "Featured Courses"),
        (LEARNING_PROGRAMS, "Learning Programs"),
        (ACHIEVEMENTS, "Achievements"),
        (TESTIMONIALS, "Testimonials"),
        (CONTACT, "Contact"),
        (CUSTOM_TEXT, "Custom Text"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="portfolio_sections",
    )
    section_type = models.CharField(max_length=40, choices=SECTION_CHOICES)
    title = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="org/portfolios/", blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["organization", "is_enabled", "display_order"], name="org_portal_section_idx")
        ]

    def __str__(self):
        return f"{self.organization.name}: {self.get_section_type_display()}"
