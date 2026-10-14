from django.core.exceptions import ValidationError
from django.db import models


class ExamTrack(models.Model):
    """
    Represents a collection/track of exams.

    A track can have:
    - Multiple exams
    - Multiple subscription plans
    - Legacy pricing configuration
    - Organization ownership
    """

    # =====================================================
    # SUBSCRIPTION SCOPE
    # =====================================================

    TRACK = "track"
    EXAM = "exam"

    SUBSCRIPTION_SCOPE_CHOICES = [
        (TRACK, "Track"),
        (EXAM, "Exam"),
    ]

    # =====================================================
    # CORE FIELDS
    # =====================================================

    title = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        help_text="Unique inside organization"
    )

    description = models.TextField(
        blank=True
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exam_tracks",
    )

    subscription_scope = models.CharField(
        max_length=10,
        choices=SUBSCRIPTION_SCOPE_CHOICES,
        default=TRACK,
    )

    # =====================================================
    # DYNAMIC PRICING
    # PRIMARY SUBSCRIPTION SYSTEM
    # =====================================================

    subscription_plans = models.ManyToManyField(
        "SubscriptionPlan",
        blank=True,
        related_name="tracks",
        help_text="Dynamic pricing plans available for this track",
    )

    # =====================================================
    # LEGACY PRICING
    # DEPRECATED
    # =====================================================

    PRICING_FREE = "free"
    PRICING_MONTHLY = "monthly"
    PRICING_LIFETIME = "lifetime"

    PRICING_TYPE_CHOICES = [
        (PRICING_FREE, "Free"),
        (PRICING_MONTHLY, "Monthly"),
        (PRICING_LIFETIME, "Lifetime"),
    ]

    pricing_type = models.CharField(
        max_length=20,
        choices=PRICING_TYPE_CHOICES,
        default=PRICING_FREE,
        help_text="⚠ Legacy pricing (avoid when using subscription plans)",
    )

    monthly_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    lifetime_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    trial_days = models.PositiveIntegerField(
        default=7,
        help_text="Trial days (legacy system)",
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:
        unique_together = (
            "organization",
            "slug",
        )

        ordering = [
            "-created_at",
        ]

    # =====================================================
    # VALIDATION
    # =====================================================

    def clean(self):
        super().clean()

        if (
            self.pricing_type == self.PRICING_MONTHLY
            and not self.monthly_price
        ):
            raise ValidationError(
                {
                    "monthly_price": (
                        "Monthly price is required "
                        "for monthly pricing."
                    )
                }
            )

        if (
            self.pricing_type == self.PRICING_LIFETIME
            and not self.lifetime_price
        ):
            raise ValidationError(
                {
                    "lifetime_price": (
                        "Lifetime price is required "
                        "for lifetime pricing."
                    )
                }
            )

    # =====================================================
    # HELPERS
    # =====================================================

    def has_dynamic_plans(self):
        """
        Returns True if at least one active
        subscription plan exists.

        Safe to call after the object has been saved.
        """

        return self.subscription_plans.filter(
            is_active=True
        ).exists()

    def is_free(self):
        """
        Track is considered free only when:

        1. There are no active dynamic subscription plans.
        2. Legacy pricing type is free.
        """

        if self.has_dynamic_plans():
            return False

        return self.pricing_type == self.PRICING_FREE

    # =====================================================
    # STRING REPRESENTATION
    # =====================================================

    def __str__(self):
        if self.organization:
            return f"{self.organization.name} → {self.title}"

        return self.title