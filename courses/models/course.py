from django.db import models
from django.conf import settings
from django.utils.text import slugify

from quiz.models import Category, SubscriptionPlan


class Course(models.Model):

    # =====================================================
    # BASIC INFORMATION
    # =====================================================

    title = models.CharField(
        max_length=255
    )

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


    # =====================================================
    # OWNERSHIP
    # =====================================================

    OWNER_PLATFORM = "platform"
    OWNER_ORGANIZATION = "organization"

    OWNER_CHOICES = (
        (OWNER_PLATFORM, "Platform"),
        (OWNER_ORGANIZATION, "Organization"),
    )

    owner_type = models.CharField(
        max_length=20,
        choices=OWNER_CHOICES,
        default=OWNER_PLATFORM,
        db_index=True
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="courses"
    )


    # =====================================================
    # VISIBILITY / PUBLICATION
    # =====================================================

    is_public = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, an approved and published course "
            "may be visible publicly."
        )
    )

    is_published = models.BooleanField(
        default=False,
        db_index=True
    )


    # =====================================================
    # COURSE APPROVAL / MODERATION
    # =====================================================

    APPROVAL_DRAFT = "draft"
    APPROVAL_PENDING = "pending"
    APPROVAL_APPROVED = "approved"
    APPROVAL_CHANGES = "changes_required"
    APPROVAL_REJECTED = "rejected"

    APPROVAL_CHOICES = (
        (
            APPROVAL_DRAFT,
            "Draft",
        ),
        (
            APPROVAL_PENDING,
            "Pending Review",
        ),
        (
            APPROVAL_APPROVED,
            "Approved",
        ),
        (
            APPROVAL_CHANGES,
            "Changes Required",
        ),
        (
            APPROVAL_REJECTED,
            "Rejected",
        ),
    )

    approval_status = models.CharField(
        max_length=30,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_DRAFT,
        db_index=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="courses_reviewed",
    )

    review_notes = models.TextField(
        blank=True,
        default="",
    )


    # =====================================================
    # SUBSCRIPTION / PRICING
    # =====================================================

    subscription_plans = models.ManyToManyField(
        SubscriptionPlan,
        blank=True,
        related_name="course_access_courses"
    )


    # =====================================================
    # AUDIT
    # =====================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="courses_created"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = [
            "-created_at"
        ]

        indexes = [

            models.Index(
                fields=[
                    "owner_type"
                ]
            ),

            models.Index(
                fields=[
                    "organization"
                ]
            ),

            models.Index(
                fields=[
                    "approval_status"
                ]
            ),

            models.Index(
                fields=[
                    "approval_status",
                    "is_published",
                    "is_public",
                ]
            ),
        ]


    # =====================================================
    # STRING
    # =====================================================

    def __str__(self):
        return self.title


    # =====================================================
    # SLUG GENERATOR
    # =====================================================

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(
                self.title
            )

            unique_slug = base_slug

            counter = 1

            while Course.objects.filter(
                slug=unique_slug
            ).exists():

                unique_slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1

            self.slug = unique_slug

        super().save(
            *args,
            **kwargs
        )


    # =====================================================
    # OWNERSHIP HELPERS
    # =====================================================

    def is_platform_course(self):

        return (
            self.owner_type
            == self.OWNER_PLATFORM
        )


    def is_organization_course(self):

        return (
            self.owner_type
            == self.OWNER_ORGANIZATION
        )


    # =====================================================
    # APPROVAL HELPERS
    # =====================================================

    def is_draft(self):

        return (
            self.approval_status
            == self.APPROVAL_DRAFT
        )


    def is_pending_review(self):

        return (
            self.approval_status
            == self.APPROVAL_PENDING
        )


    def is_approved(self):

        return (
            self.approval_status
            == self.APPROVAL_APPROVED
        )


    def requires_changes(self):

        return (
            self.approval_status
            == self.APPROVAL_CHANGES
        )


    def is_rejected(self):

        return (
            self.approval_status
            == self.APPROVAL_REJECTED
        )


    # =====================================================
    # PUBLIC AVAILABILITY
    # =====================================================

    def is_publicly_available(self):

        return (
            self.approval_status
            == self.APPROVAL_APPROVED
            and self.is_published
            and self.is_public
        )