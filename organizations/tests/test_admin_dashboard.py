from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models import Organization, OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


class OrganizationAdminDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", password="test-password")
        self.other_org = Organization.objects.create(name="Other School", slug="other-school", created_by=self.owner)
        self.organization = Organization.objects.create(name="School", slug="school", created_by=self.owner)
        OrganizationMember.objects.create(
            user=self.owner,
            organization=self.organization,
            role=OrganizationRole.ORG_OWNER,
            is_active=True,
        )
        self.client = Client()
        self.client.force_login(self.owner)

    def test_dashboard_route_uses_organization_dashboard(self):
        response = self.client.get(reverse("organizations_admin:dashboard", kwargs={"slug": self.organization.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization Dashboard")
        self.assertContains(response, "Search this organization")
        self.assertContains(response, "Manage students")
        self.assertContains(response, reverse("organizations_admin:courses", kwargs={"slug": self.organization.slug}))

    def test_autocomplete_is_organization_scoped_and_prefix_matched(self):
        Course.objects.create(
            title="Test Course",
            description="Organization course",
            level="beginner",
            owner_type=Course.OWNER_ORGANIZATION,
            organization=self.organization,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )
        Course.objects.create(
            title="Test Other Course",
            description="Other organization course",
            level="beginner",
            owner_type=Course.OWNER_ORGANIZATION,
            organization=self.other_org,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
            created_by=self.owner,
        )

        response = self.client.get(
            reverse("organizations_admin:autocomplete", kwargs={"slug": self.organization.slug}),
            {"q": "t"},
        )
        self.assertEqual(response.status_code, 200)
        labels = [item["label"] for item in response.json()["results"]]
        self.assertIn("Test Course", labels)
        self.assertNotIn("Test Other Course", labels)

    def test_search_requires_organization_admin_access(self):
        outsider = get_user_model().objects.create_user(username="outsider", password="test-password")
        self.client.force_login(outsider)
        response = self.client.get(
            reverse("organizations_admin:search", kwargs={"slug": self.organization.slug}),
            {"q": "test"},
        )
        self.assertIn(response.status_code, {302, 403})
