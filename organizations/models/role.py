# organizations/models/role.py

from django.db import models


class OrganizationRole(models.TextChoices):
    """
    Roles available within an organization.

    These define the user's organization-level identity.
    Fine-grained authorization is handled separately by
    organizations.permissions and the service layer.
    """

    # =========================================================
    # ORGANIZATION ADMINISTRATION
    # =========================================================

    ORG_OWNER = "org_owner", "Organization Owner"

    ORG_ADMIN = "org_admin", "Organization Admin"

    # =========================================================
    # STAFF / TEACHING
    # =========================================================

    STAFF = "staff", "Staff / Teacher"

    # =========================================================
    # STUDENT
    # =========================================================

    STUDENT = "student", "Student"

    # =========================================================
    # ROLE GROUPS
    # =========================================================

    @classmethod
    def administrative_roles(cls):
        """
        Roles with organization administration capability.
        """

        return {
            cls.ORG_OWNER,
            cls.ORG_ADMIN,
        }

    @classmethod
    def teaching_roles(cls):
        """
        Roles capable of teaching/content operations.

        Owners and admins are included because they have
        organization-level authority.
        """

        return {
            cls.ORG_OWNER,
            cls.ORG_ADMIN,
            cls.STAFF,
        }

    @classmethod
    def all_roles(cls):
        """
        Return all organization roles.
        """

        return {
            cls.ORG_OWNER,
            cls.ORG_ADMIN,
            cls.STAFF,
            cls.STUDENT,
        }

    # =========================================================
    # VALIDATION / CAPABILITY HELPERS
    # =========================================================

    @classmethod
    def is_valid_role(cls, role):
        """
        Return True when the supplied value is a valid
        organization role.
        """

        return role in cls.all_roles()

    @classmethod
    def is_administrator(cls, role):
        """
        Return True for organization owners and administrators.
        """

        return role in cls.administrative_roles()

    @classmethod
    def is_teacher(cls, role):
        """
        Return True for roles that can potentially perform
        teaching/content operations.
        """

        return role in cls.teaching_roles()

    @classmethod
    def is_student(cls, role):
        """
        Return True when the role represents a student.
        """

        return role == cls.STUDENT