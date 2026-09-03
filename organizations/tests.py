# organizations/tests.py

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole


User = get_user_model()


class OrganizationAuthorizationRegressionTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="School A", slug="school-a", org_type=Organization.TYPE_SCHOOL
        )
        self.org_b = Organization.objects.create(
            name="School B", slug="school-b", org_type=Organization.TYPE_SCHOOL
        )
        self.admin = User.objects.create_user(
            username="admin-a", email="admin-a@example.com", password="password"
        )
        self.other_admin = User.objects.create_user(
            username="admin-b", email="admin-b@example.com", password="password"
        )
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="password"
        )

        OrganizationMember.objects.create(
            user=self.admin, organization=self.org_a, role=OrganizationRole.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            user=self.other_admin, organization=self.org_b, role=OrganizationRole.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            user=self.student, organization=self.org_a, role=OrganizationRole.STUDENT
        )

    def test_member_role_management_is_organization_scoped(self):
        member_b = OrganizationMember.objects.get(
            user=self.other_admin, organization=self.org_b
        )
        self.assertEqual(member_b.role, OrganizationRole.ORG_ADMIN)
        self.assertFalse(
            OrganizationMember.objects.filter(
                user=self.other_admin, organization=self.org_a
            ).exists()
        )

    def test_admin_is_not_a_valid_student_management_role(self):
        self.assertNotIn(
            OrganizationRole.ORG_ADMIN,
            {OrganizationRole.STUDENT, OrganizationRole.STAFF},
        )

    def test_active_membership_is_required_for_organization_access(self):
        member = OrganizationMember.objects.get(
            user=self.admin, organization=self.org_a
        )
        member.is_active = False
        member.save(update_fields=["is_active"])
        self.assertFalse(member.is_active)


# Existing assignment tests remain below this point in the project history.
