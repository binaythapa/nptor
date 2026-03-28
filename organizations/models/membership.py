from django.db import models
from django.contrib.auth.models import User
from .organization import Organization


# =====================================================
# ORGANIZATION GROUP (CLASS / BATCH)
# =====================================================

class OrganizationGroup(models.Model):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="groups"
    )

    name = models.CharField(max_length=100)   # e.g. Class 1, Batch A
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


# =====================================================
# ORGANIZATION MEMBER
# =====================================================

class OrganizationMember(models.Model):

    ROLE_CHOICES = (
        ("org_admin", "Organization Admin"),
        ("staff", "Staff / Teacher"),
        ("student", "Student"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members"
    )

    # 🔥 NEW FIELD (GROUP SUPPORT)
    group = models.ForeignKey(
        OrganizationGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members"
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user} → {self.organization} ({self.role})"