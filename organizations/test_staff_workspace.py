from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.portal import OrganizationPortalConfig
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
        OrganizationPortalConfig.objects.filter(organization=self.organization).update(
            is_published=False,
        )
        self.staff = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="password",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.staff,
            organization=self.organization,
            role=OrganizationRole.STAFF,
        )
        OrganizationMember.objects.create(
            user=self.student,
            organization=self.organization,
            role=OrganizationRole.STUDENT,
        )

    def test_staff_can_open_organization_workspace_when_public_portal_is_unpublished(self):
        self.client.force_login(self.staff)
        response = self.client.get("/org/test-school/workspace/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization Workspace")
        self.assertContains(response, "Test School")

    def test_student_cannot_open_staff_organization_workspace(self):
        self.client.force_login(self.student)
        response = self.client.get("/org/test-school/workspace/")

        self.assertEqual(response.status_code, 403)
