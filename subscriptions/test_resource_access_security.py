from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models.access import ResourceAccess
from organizations.models.organization import Organization


User = get_user_model()


class ResourceAccessSecurityTests(TestCase):
    def test_organization_access_is_invalid_for_inactive_membership(self):
        user = User.objects.create_user(
            username="access_security_user",
            password="testpass123",
        )
        organization = Organization.objects.create(
            name="Access Security Org",
            slug="access-security-org",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )

        access = ResourceAccess(
            user=user,
            resource_type=ResourceAccess.RESOURCE_COURSE,
            source=ResourceAccess.SOURCE_ORGANIZATION,
            organization=organization,
            is_active=True,
        )

        with patch(
            "organizations.models.access.OrganizationMember.objects.filter"
        ) as membership_filter:
            membership_filter.return_value.exists.return_value = False

            self.assertFalse(access.is_valid())

            membership_filter.assert_called_once_with(
                user=user,
                organization=organization,
                is_active=True,
            )
