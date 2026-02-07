from django.db import models


class OrganizationRole(models.TextChoices):
    ORG_ADMIN = "org_admin", "Organization Admin"
    STAFF = "staff", "Staff / Teacher"
    STUDENT = "student", "Student"
