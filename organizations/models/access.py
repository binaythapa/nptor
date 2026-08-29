# organizations/models/access.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ResourceAccess(models.Model):
    """
    Final user-level authorization record for a learning resource.

    ResourceAccess answers:

        "Does this specific user have access to this
         specific resource?"

    Supported resources:

        - Course
        - Exam Track
        - Exam

    Access may originate from:

        - Public access
        - Individual purchase/subscription
        - Organization assignment
        - Administrator grant

    Important architectural rule:

        ResourceAccess represents ACCESS.

        It does not own:
            - subscriptions
            - assignments
            - courses
            - exams
            - organizations

        Those domains remain owned by their respective apps.

    This model only connects them at the authorization boundary.
    """

    # =========================================================
    # RESOURCE TYPES
    # =========================================================

    RESOURCE_COURSE = "course"
    RESOURCE_TRACK = "track"
    RESOURCE_EXAM = "exam"

    RESOURCE_TYPE_CHOICES = (
        (
            RESOURCE_COURSE,
            "Course",
        ),
        (
            RESOURCE_TRACK,
            "Exam Track",
        ),
        (
            RESOURCE_EXAM,
            "Exam",
        ),
    )

    # =========================================================
    # ACCESS SOURCES
    # =========================================================

    SOURCE_PUBLIC = "public"
    SOURCE_INDIVIDUAL = "individual"
    SOURCE_ORGANIZATION = "organization"
    SOURCE_ADMIN = "admin"

    ACCESS_SOURCE_CHOICES = (
        (
            SOURCE_PUBLIC,
            "Public",
        ),
        (
            SOURCE_INDIVIDUAL,
            "Individual Purchase",
        ),
        (
            SOURCE_ORGANIZATION,
            "Organization Assignment",
        ),
        (
            SOURCE_ADMIN,
            "Administrator",
        ),
    )

    # =========================================================
    # USER
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resource_access",
    )

    # =========================================================
    # RESOURCE TYPE
    # =========================================================

    resource_type = models.CharField(
        max_length=20,
        choices=RESOURCE_TYPE_CHOICES,
        db_index=True,
    )

    # =========================================================
    # RESOURCES
    # =========================================================

    course = models.ForeignKey(
        "courses.Course",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_access_records",
    )

    track = models.ForeignKey(
        "quiz.ExamTrack",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_access_records",
    )

    exam = models.ForeignKey(
        "quiz.Exam",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_access_records",
    )

    # =========================================================
    # SOURCE
    # =========================================================

    source = models.CharField(
        max_length=20,
        choices=ACCESS_SOURCE_CHOICES,
        db_index=True,
    )

    # =========================================================
    # ORGANIZATION
    # =========================================================

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="resource_access",
    )

    # =========================================================
    # SUBSCRIPTION
    # =========================================================

    subscription = models.ForeignKey(
        "subscriptions.Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resource_access",
    )

    # =========================================================
    # ASSIGNMENT
    # =========================================================

    assignment = models.ForeignKey(
        "organizations.ResourceAssignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resource_access",
    )

    # =========================================================
    # VALIDITY
    # =========================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # AUDIT
    # =========================================================

    granted_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # ACCESS KEY
    # =========================================================
    #
    # MySQL does not reliably enforce uniqueness across
    # nullable columns.
    #
    # Therefore we maintain one deterministic logical key.
    #
    # Example:
    #
    # user:1
    # organization:5
    # source:organization
    # resource:course:42
    #
    # becomes:
    #
    # 1:5:organization:course:42
    #
    # This gives us database-level duplicate protection.
    # =========================================================

    
    access_key = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
        #db_index=True,
    )
    
   
    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = [
            "-granted_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "resource_type",
                    "is_active",
                ],
                name="res_access_user_idx",
            ),
            models.Index(
                fields=[
                    "organization",
                    "resource_type",
                    "is_active",
                ],
                name="res_access_org_idx",
            ),
            models.Index(
                fields=[
                    "subscription",
                    "is_active",
                ],
                name="res_access_sub_idx",
            ),
            models.Index(
                fields=[
                    "assignment",
                    "is_active",
                ],
                name="res_access_assign_idx",
            ),
            models.Index(
                fields=[
                    "expires_at",
                    "is_active",
                ],
                name="res_access_exp_idx",
            ),
        ]

    # =========================================================
    # RESOURCE HELPERS
    # =========================================================

    def get_resource(self):
        """
        Return the actual resource represented by this record.
        """

        if self.resource_type == self.RESOURCE_COURSE:
            return self.course

        if self.resource_type == self.RESOURCE_TRACK:
            return self.track

        if self.resource_type == self.RESOURCE_EXAM:
            return self.exam

        return None

    def get_resource_id(self):
        """
        Return the primary key of the selected resource.
        """

        resource = self.get_resource()

        if resource is None:
            return None

        return resource.pk

    # =========================================================
    # ACCESS KEY
    # =========================================================

    def build_access_key(self):
        """
        Build the unique logical identity of this access record.
        """

        resource_id = self.get_resource_id()

        if not self.user_id:
            return None

        if not self.resource_type:
            return None

        if not self.source:
            return None

        if resource_id is None:
            return None

        organization_id = (
            self.organization_id
            if self.organization_id
            else 0
        )

        return (
            f"{self.user_id}:"
            f"{organization_id}:"
            f"{self.source}:"
            f"{self.resource_type}:"
            f"{resource_id}"
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        # =====================================================
        # RESOURCE TYPE
        # =====================================================

        valid_resource_types = {
            self.RESOURCE_COURSE,
            self.RESOURCE_TRACK,
            self.RESOURCE_EXAM,
        }

        if self.resource_type not in valid_resource_types:

            raise ValidationError({
                "resource_type": (
                    "Invalid resource type."
                )
            })

        # =====================================================
        # SOURCE
        # =====================================================

        valid_sources = {
            self.SOURCE_PUBLIC,
            self.SOURCE_INDIVIDUAL,
            self.SOURCE_ORGANIZATION,
            self.SOURCE_ADMIN,
        }

        if self.source not in valid_sources:

            raise ValidationError({
                "source": (
                    "Invalid access source."
                )
            })

        # =====================================================
        # EXACTLY ONE RESOURCE
        # =====================================================

        resources = {
            self.RESOURCE_COURSE: self.course,
            self.RESOURCE_TRACK: self.track,
            self.RESOURCE_EXAM: self.exam,
        }

        selected_resource = resources.get(
            self.resource_type
        )

        if selected_resource is None:

            raise ValidationError({
                "resource_type": (
                    "The selected resource must be provided."
                )
            })

        for resource_type, resource in resources.items():

            if (
                resource_type != self.resource_type
                and resource is not None
            ):

                raise ValidationError({
                    "resource_type": (
                        "Only one resource type can be "
                        "associated with an access record."
                    )
                })

        # =====================================================
        # ORGANIZATION ACCESS
        # =====================================================

        if self.source == self.SOURCE_ORGANIZATION:

            if not self.organization_id:

                raise ValidationError({
                    "organization": (
                        "Organization is required for "
                        "organization access."
                    )
                })

            if (
                self.organization
                and not self.organization.is_active
            ):

                raise ValidationError({
                    "organization": (
                        "Access cannot be granted through "
                        "an inactive organization."
                    )
                })

        else:

            if self.organization_id:

                raise ValidationError({
                    "organization": (
                        "Organization is only allowed for "
                        "organization access."
                    )
                })

        # =====================================================
        # ASSIGNMENT
        # =====================================================

        if self.assignment_id:

            if self.source != self.SOURCE_ORGANIZATION:

                raise ValidationError({
                    "assignment": (
                        "Assignment is only valid for "
                        "organization access."
                    )
                })

            assignment = self.assignment

            # -------------------------------------------------
            # Student consistency
            # -------------------------------------------------

            if (
                assignment.student_id
                != self.user_id
            ):

                raise ValidationError({
                    "assignment": (
                        "Assignment student does not "
                        "match the access user."
                    )
                })

            # -------------------------------------------------
            # Organization consistency
            # -------------------------------------------------

            if (
                self.organization_id
                and assignment.organization_id
                != self.organization_id
            ):

                raise ValidationError({
                    "assignment": (
                        "Assignment organization does not "
                        "match access organization."
                    )
                })

        # =====================================================
        # SUBSCRIPTION
        # =====================================================

        if self.subscription_id:

            subscription = self.subscription

            # -------------------------------------------------
            # Organization subscription
            # -------------------------------------------------

            if self.source == self.SOURCE_ORGANIZATION:

                subscription_org_id = getattr(
                    subscription,
                    "organization_id",
                    None,
                )

                # If the subscription belongs to an
                # organization, it must be the same organization.
                if (
                    subscription_org_id
                    and subscription_org_id
                    != self.organization_id
                ):

                    raise ValidationError({
                        "subscription": (
                            "Subscription organization does not "
                            "match access organization."
                        )
                    })

            # -------------------------------------------------
            # Individual subscription
            # -------------------------------------------------

            if (
                self.source == self.SOURCE_INDIVIDUAL
                and subscription.user_id
                != self.user_id
            ):

                raise ValidationError({
                    "subscription": (
                        "Subscription user does not "
                        "match access user."
                    )
                })

        # =====================================================
        # EXPIRATION
        # =====================================================

        if self.expires_at:

            comparison_time = (
                self.granted_at
                or timezone.now()
            )

            if self.expires_at <= comparison_time:

                raise ValidationError({
                    "expires_at": (
                        "Expiration must be later than "
                        "the access grant time."
                    )
                })

        # =====================================================
        # ACTIVE / REVOKED CONSISTENCY
        # =====================================================

        if self.is_active and self.revoked_at:

            raise ValidationError({
                "revoked_at": (
                    "Active access cannot have a "
                    "revocation timestamp."
                )
            })

    # =========================================================
    # SAVE
    # =========================================================

    def save(
        self,
        *args,
        **kwargs,
    ):
        """
        Generate the logical access key before saving.

        full_clean() is intentionally performed here so that
        programmatic saves also receive model validation.

        Service-layer validation should still be used for
        complex business rules.
        """

        self.full_clean()

        access_key = self.build_access_key()

        if not access_key:

            raise ValidationError(
                "Unable to generate access key. "
                "User, source, resource type and resource "
                "are required."
            )

        self.access_key = access_key

        super().save(
            *args,
            **kwargs,
        )

    # =========================================================
    # EXPIRATION
    # =========================================================

    def has_expired(self):
        """
        Return True when the access has passed its expiration.
        """

        if self.expires_at is None:
            return False

        return timezone.now() >= self.expires_at

    # =========================================================
    # VALIDITY
    # =========================================================

    def is_valid(self):
        """
        Return True only when the access record is currently
        usable.
        """

        if not self.is_active:
            return False

        if self.revoked_at:
            return False

        if self.has_expired():
            return False

        # -----------------------------------------------------
        # Subscription-backed access
        # -----------------------------------------------------

        if self.subscription_id:

            if not self.subscription.is_valid():
                return False

        # -----------------------------------------------------
        # Organization-backed access
        # -----------------------------------------------------

        if self.organization_id:

            if not self.organization.is_active:
                return False

        # -----------------------------------------------------
        # Assignment-backed access
        # -----------------------------------------------------

        if self.assignment_id:

            # Do not assume every assignment implementation
            # has is_active. Check it only when available.

            if hasattr(
                self.assignment,
                "is_active",
            ):

                if not self.assignment.is_active:
                    return False

        return True

    # =========================================================
    # REVOKE
    # =========================================================

    def revoke(self):
        """
        Permanently revoke this access record.

        The record is retained for audit/history.
        """

        if self.revoked_at:
            return

        self.is_active = False
        self.revoked_at = timezone.now()

        self.save(
            update_fields=[
                "is_active",
                "revoked_at",
                "updated_at",
            ]
        )

    # =========================================================
    # ACTIVATE
    # =========================================================

    def activate(self):
        """
        Reactivate access.

        Expired access cannot simply be reactivated without
        updating expires_at through the appropriate service.
        """

        if (
            self.expires_at
            and timezone.now() >= self.expires_at
        ):

            raise ValidationError(
                "Expired access cannot be activated "
                "without extending its expiration."
            )

        self.is_active = True
        self.revoked_at = None

        self.save(
            update_fields=[
                "is_active",
                "revoked_at",
                "updated_at",
            ]
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):

        resource = self.get_resource()

        if resource:

            return (
                f"{self.user} → "
                f"{resource} "
                f"({self.source})"
            )

        return (
            f"{self.user} → "
            f"Resource Access"
        )