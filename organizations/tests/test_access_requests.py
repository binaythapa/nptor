from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models import Organization, OrganizationAccessRequest, OrganizationRole


class OrganizationAccessRequestModelTests(TestCase):
    def test_access_request_can_be_created_with_pending_status(self):
        User = get_user_model()
        user = User.objects.create_user(username="requester", password="testpass123")
        organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            org_type="school",
            created_by=user,
        )

        request = OrganizationAccessRequest.objects.create(
            user=user,
            organization=organization,
            service=OrganizationAccessRequest.SERVICE_ORGANIZATION_ACCESS,
            requested_role=OrganizationRole.STUDENT,
            reason="I need access.",
        )

        self.assertEqual(request.status, OrganizationAccessRequest.STATUS_PENDING)
        self.assertEqual(request.user, user)
        self.assertEqual(request.organization, organization)
