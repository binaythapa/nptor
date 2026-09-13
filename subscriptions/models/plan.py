from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class SubscriptionPlan(models.Model):

    # Legacy scope is retained during migration; product_type/access_mode are
    # the authoritative commerce model going forward.
    SCOPE_RESOURCE = "resource"
    SCOPE_ALL_ACCESS = "all_access"

    SCOPE_CHOICES = (
        (SCOPE_RESOURCE, "Resource"),
        (SCOPE_ALL_ACCESS, "All Access"),
    )

    PRODUCT_COURSE = "course"
    PRODUCT_TRACK = "track"
    PRODUCT_ACCOUNT = "account"

    PRODUCT_CHOICES = (
        (PRODUCT_COURSE, "Course"),
        (PRODUCT_TRACK, "Track"),
        (PRODUCT_ACCOUNT, "Account"),
    )

    ACCESS_SINGLE_RESOURCE = "single_resource"
    ACCESS_LIMITED = "limited_access"
    ACCESS_ALL = "all_access"

    ACCESS_MODE_CHOICES = (
        (ACCESS_SINGLE_RESOURCE, "Single Resource"),
        (ACCESS_LIMITED, "Limited Access"),
        (ACCESS_ALL, "All Access"),
    )

    INTERVAL_DAY = "day"
    INTERVAL_WEEK = "week"
    INTERVAL_MONTH = "month"
    INTERVAL_YEAR = "year"
    INTERVAL_LIFETIME = "lifetime"

    INTERVAL_CHOICES = (
        (INTERVAL_DAY, "Day"),
        (INTERVAL_WEEK, "Week"),
        (INTERVAL_MONTH, "Month"),
        (INTERVAL_YEAR, "Year"),
        (INTERVAL_LIFETIME, "Lifetime"),
    )

    name = models.CharField(max_length=100)

    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique internal identifier for this plan.",
    )

    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_RESOURCE,
        db_index=True,
        help_text="Legacy scope retained for migration compatibility.",
    )

    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_CHOICES,
        default=PRODUCT_COURSE,
        db_index=True,
        help_text="What this plan sells: a Course, Track, or Account.",
    )

    access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_MODE_CHOICES,
        default=ACCESS_SINGLE_RESOURCE,
        db_index=True,
        help_text="Account plans may be limited by selectable Course/Track quotas or all-access.",
    )

    max_courses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum Courses selectable for a limited Account plan. NULL means not applicable/unlimited by this field.",
    )

    max_tracks = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum Tracks selectable for a limited Account plan. NULL means not applicable/unlimited by this field.",
    )

    description = models.TextField(blank=True, default="")

    # Legacy duration is retained so existing records remain readable while
    # new plans use the explicit calendar-aware billing interval below.
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Legacy duration in days. NULL means lifetime for legacy plans.",
    )

    interval_unit = models.CharField(
        max_length=10,
        choices=INTERVAL_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text="Billing interval unit. Use Lifetime for one-time lifetime access.",
    )

    interval_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of interval units in one billing period. Not used for Lifetime.",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(max_length=10, default="INR")

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["scope", "is_active"]),
            models.Index(fields=["product_type", "access_mode", "is_active"]),
            models.Index(fields=["interval_unit", "is_active"]),
        ]

    def clean(self):
        super().clean()

        if self.product_type in (self.PRODUCT_COURSE, self.PRODUCT_TRACK):
            if self.access_mode != self.ACCESS_SINGLE_RESOURCE:
                raise ValidationError({"access_mode": "Course and Track plans must use single-resource access."})
            if self.max_courses is not None or self.max_tracks is not None:
                raise ValidationError("Course and Track plans cannot define account quotas.")
        elif self.product_type == self.PRODUCT_ACCOUNT:
            if self.access_mode == self.ACCESS_LIMITED:
                if (self.max_courses or 0) + (self.max_tracks or 0) <= 0:
                    raise ValidationError("A limited Account plan must allow at least one Course or Track.")
            elif self.access_mode == self.ACCESS_ALL:
                if self.max_courses is not None or self.max_tracks is not None:
                    raise ValidationError("All-access Account plans cannot define quotas.")
            else:
                raise ValidationError({"access_mode": "Account plans must use limited_access or all_access."})

        if self.interval_unit == self.INTERVAL_LIFETIME:
            if self.interval_count is not None:
                raise ValidationError({"interval_count": "Lifetime plans do not use an interval count."})
        elif self.interval_unit:
            if not self.interval_count or self.interval_count <= 0:
                raise ValidationError({"interval_count": "A positive interval count is required for time-based plans."})
        elif self.interval_count is not None:
            raise ValidationError({"interval_unit": "Select an interval unit when an interval count is supplied."})

    def is_lifetime(self):
        if self.interval_unit:
            return self.interval_unit == self.INTERVAL_LIFETIME
        return self.duration_days is None

    def get_billing_interval_label(self):
        if self.is_lifetime():
            return "Lifetime"
        count = self.interval_count
        unit = self.get_interval_unit_display().lower()
        return f"{count} {unit}{'' if count == 1 else 's'}"

    def is_all_access(self):
        return self.product_type == self.PRODUCT_ACCOUNT and self.access_mode == self.ACCESS_ALL

    def is_account_plan(self):
        return self.product_type == self.PRODUCT_ACCOUNT

    def is_limited_account_plan(self):
        return self.product_type == self.PRODUCT_ACCOUNT and self.access_mode == self.ACCESS_LIMITED

    def __str__(self):
        return self.name
