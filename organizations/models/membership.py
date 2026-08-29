# organizations/models/membership.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .organization import Organization
from .role import OrganizationRole


class OrganizationMember(models.Model):
    """
    Represents a user's membership in an organization.

    A user may belong to multiple organizations and may have
    a different role in each organization.

    Example:

        User A
            ├── School A → org_admin
            └── Institute B → staff

    Membership defines the user's organization-level identity.

    Fine-grained permissions are handled separately by:

        organizations.permissions
    """

    # =========================================================
    # ROLE CONSTANTS
    # =========================================================
    #
    # Backward-compatible aliases.
    #
    # Existing application code can continue using:
    #
    #     OrganizationMember.ROLE_ORG_ADMIN
    #     OrganizationMember.ROLE_STAFF
    #     OrganizationMember.ROLE_STUDENT
    #
    # while the actual source of truth remains OrganizationRole.
    # =========================================================

    ROLE_ORG_OWNER = OrganizationRole.ORG_OWNER
    ROLE_ORG_ADMIN = OrganizationRole.ORG_ADMIN
    ROLE_STAFF = OrganizationRole.STAFF
    ROLE_STUDENT = OrganizationRole.STUDENT

    ROLE_CHOICES = OrganizationRole.choices

    # =========================================================
    # MEMBERSHIP
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        help_text="User's role within this organization.",
    )

    # =========================================================
    # STATUS
    # =========================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Inactive members cannot access organization "
            "resources."
        ),
    )

    # =========================================================
    # AUDIT
    # =========================================================

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # META
    # =========================================================

    class Meta:
        ordering = [
            "organization",
            "user",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "organization",
                ],
                name="unique_org_member",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "is_active",
                ],
                name="org_member_active_idx",
            ),
            models.Index(
                fields=[
                    "organization",
                    "role",
                    "is_active",
                ],
                name="org_member_role_idx",
            ),
            models.Index(
                fields=[
                    "user",
                    "is_active",
                ],
                name="org_member_user_idx",
            ),
        ]

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        super().clean()

        if not self.user_id:
            raise ValidationError({
                "user": "A user is required.",
            })

        if not self.organization_id:
            raise ValidationError({
                "organization": (
                    "An organization is required."
                ),
            })

        if not self.role:
            raise ValidationError({
                "role": (
                    "An organization membership role "
                    "is required."
                ),
            })

        if not OrganizationRole.is_valid_role(
            self.role
        ):
            raise ValidationError({
                "role": (
                    "Invalid organization membership role."
                ),
            })

        # -----------------------------------------------------
        # Organization status
        # -----------------------------------------------------

        if (
            self.organization_id
            and self.organization
            and not self.organization.is_active
            and self.is_active
        ):
            raise ValidationError({
                "is_active": (
                    "A member cannot be active in an "
                    "inactive organization."
                ),
            })

    # =========================================================
    # ROLE HELPERS
    # =========================================================

    @property
    def is_org_owner(self):
        """
        True when this member is an active organization owner.
        """

        return (
            self.is_active
            and self.role == OrganizationRole.ORG_OWNER
        )

    @property
    def is_org_admin(self):
        """
        True when this member is an active organization admin.

        Organization owners are intentionally not included here.
        Use is_org_owner or is_administrator when owner-level
        access is required.
        """

        return (
            self.is_active
            and self.role == OrganizationRole.ORG_ADMIN
        )

    @property
    def is_staff_member(self):
        """
        True when this member is an active staff/teacher.
        """

        return (
            self.is_active
            and self.role == OrganizationRole.STAFF
        )

    @property
    def is_student(self):
        """
        True when this member is an active student.
        """

        return (
            self.is_active
            and self.role == OrganizationRole.STUDENT
        )

    @property
    def is_administrator(self):
        """
        True for both organization owners and admins.
        """

        return (
            self.is_active
            and OrganizationRole.is_administrator(
                self.role
            )
        )

    @property
    def is_teacher(self):
        """
        True for roles that can potentially perform
        teaching/content operations.

        Actual authorization must still be handled by
        organizations.permissions.
        """

        return (
            self.is_active
            and OrganizationRole.is_teacher(
                self.role
            )
        )

    # =========================================================
    # ACCESS / CAPABILITY HELPERS
    # =========================================================

    @property
    def can_manage_students(self):
        """
        Indicates whether this role can potentially manage
        students.

        This is a capability helper only.

        Final authorization must be performed by the
        organization's permission layer.
        """

        return (
            self.is_active
            and self.role in {
                OrganizationRole.ORG_OWNER,
                OrganizationRole.ORG_ADMIN,
                OrganizationRole.STAFF,
            }
        )

    @property
    def can_manage_content(self):
        """
        Indicates whether this role can potentially manage
        learning content.
        """

        return (
            self.is_active
            and self.role in {
                OrganizationRole.ORG_OWNER,
                OrganizationRole.ORG_ADMIN,
                OrganizationRole.STAFF,
            }
        )

    @property
    def can_manage_organization(self):
        """
        Organization-level management capability.

        Owners and administrators can manage the organization.
        Staff/teachers and students cannot.
        """

        return (
            self.is_active
            and self.role in {
                OrganizationRole.ORG_OWNER,
                OrganizationRole.ORG_ADMIN,
            }
        )

    # =========================================================
    # STRING
    # =========================================================

    def __str__(self):
        return (
            f"{self.user} → "
            f"{self.organization} "
            f"({self.get_role_display()})"
        )