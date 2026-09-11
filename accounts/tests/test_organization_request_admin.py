from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.access_request import OrganizationAccessRequest
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole


class OrganizationRequestAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin", password="test-password", is_superuser=True, is_staff=True)
        self.user = User.objects.create_user(username="user", password="test-password")
        self.organization = Organization.objects.create(name="School", slug="school", created_by=self.admin)
        self.access_request = OrganizationAccessRequest.objects.create(user=self.user, organization=self.organization, requested_role=OrganizationRole.STUDENT)

    def test_non_admin_cannot_view_request_center(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:organization_requests"))
        self.assertEqual(response.status_code, 403)

    def test_platform_admin_can_view_and_approve_request(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:organization_request_detail", kwargs={"pk": self.access_request.pk}))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("accounts:organization_request_approve", kwargs={"pk": self.access_request.pk}), {"review_notes": "Approved"})
        self.assertEqual(response.status_code, 302)
        self.access_request.refresh_from_db()
        self.assertEqual(self.access_request.status, OrganizationAccessRequest.STATUS_APPROVED)
