from django.conf import settings
from django.db import models


class Organization(models.Model):
    """
    Tenant / organization within the platform.

    An organization represents an independent customer such as:

    - School
    - College
    - Training Institute
    - Company

    Organization-owned resources and members must always be
    isolated from other organizations.
    """

    # =========================================================
    # ORGANIZATION TYPES
    # =========================================================

    TYPE_SCHOOL = "school"
    TYPE_COLLEGE = "college"
    TYPE_INSTITUTE = "institute"
    TYPE_COMPANY = "company"

    ORG_TYPE_CHOICES = (
        (TYPE_SCHOOL, "School"),
        (TYPE_COLLEGE, "College"),
        (TYPE_INSTITUTE, "Training Institute"),
        (TYPE_COMPANY, "Company"),
    )

    # =========================================================
    # CORE
    # =========================================================

    name = models.CharField(
        max_length=255,
        help_text="Official organization name.",
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Unique platform identifier for the organization.",
    )

    org_type = models.CharField(
        max_length=20,
        choices=ORG_TYPE_CHOICES,
        help_text="Type of organization.",
    )

    # =========================================================
    # BRANDING
    # =========================================================

    logo = models.ImageField(
        upload_to="org/logos/",
        blank=True,
        null=True,
    )

    primary_color = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Primary branding color, e.g. #3273dc.",
    )

    # =========================================================
    # STATUS
    # =========================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Inactive organizations cannot use organization "
            "services."
        ),
    )

    # =========================================================
    # AUDIT
    # =========================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizations_created",
        help_text="User who created the organization.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["is_active", "org_type"],
                name="org_active_type_idx",
            ),
        ]

    # =========================================================
    # HELPERS
    # =========================================================

    def __str__(self):
        return self.name