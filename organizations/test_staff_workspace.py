from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole

User = get_user_model()


class StaffOrganizationWorkspaceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test School",
            slug="test-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.organization.portal_config.is_published = False
        self.organization.portal_config.save(update_fields=["is_published"])
        self.staff = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.staff,
            organization=self.organization,
            role=OrganizationRole.STAFF,
        )

    def test_staff_can_open_organization_workspace_when_public_portal_is_unpublished(self):
        self.client.force_login(self.staff)
        response = self.client.get("/org/test-school/workspace/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization Workspace")
        self.assertContains(response, "Test School")
