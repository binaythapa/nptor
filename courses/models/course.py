from django.db import models
from django.conf import settings
from django.utils.text import slugify

from quiz.models import Category, SubscriptionPlan


# =====================================================
# COURSE
# =====================================================

class Course(models.Model):

    # -------------------------------------------------
    # BASIC INFORMATION
    # -------------------------------------------------

    title = models.CharField(max_length=255)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    description = models.TextField()

    thumbnail = models.ImageField(
        upload_to="courses/",
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ]
    )

    # -------------------------------------------------
    # OWNERSHIP (PLATFORM vs ORGANIZATION)
    # -------------------------------------------------

    OWNER_CHOICES = (
        ("platform", "Platform"),
        ("organization", "Organization"),
    )

    owner_type = models.CharField(
        max_length=20,
        choices=OWNER_CHOICES,
        default="platform",
        db_index=True
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="courses"
    )

    # -------------------------------------------------
    # ACCESS CONTROL
    # -------------------------------------------------

    is_public = models.BooleanField(
        default=True,
        help_text="If true, course visible outside organization"
    )

    is_published = models.BooleanField(
        default=False,
        db_index=True
    )

    # -------------------------------------------------
    # SUBSCRIPTION / PRICING
    # -------------------------------------------------

    subscription_plans = models.ManyToManyField(
        SubscriptionPlan,
        blank=True,
        related_name="course_access_courses"
    )

    # -------------------------------------------------
    # AUDIT
    # -------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="courses_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # -------------------------------------------------
    # META
    # -------------------------------------------------

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["owner_type"]),
            models.Index(fields=["organization"]),
        ]

    # -------------------------------------------------
    # STRING
    # -------------------------------------------------

    def __str__(self):
        return self.title

    # -------------------------------------------------
    # SLUG GENERATOR
    # -------------------------------------------------

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1

            while Course.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = unique_slug

        super().save(*args, **kwargs)

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def is_platform_course(self):
        return self.owner_type == "platform"

    def is_organization_course(self):
        return self.owner_type == "organization"