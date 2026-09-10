from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole


User = get_user_model()


class StaffRoleManagementUITests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Role UI School",
            slug="role-ui-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.staff = User.objects.create_user(
            username="role-ui-staff",
            email="role-ui-staff@example.com",
            password="password",
        )
        self.student = User.objects.create_user(
            username="role-ui-student",
            email="role-ui-student@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.staff,
            organization=self.org,
            role=OrganizationRole.STAFF,
        )
        OrganizationMember.objects.create(
            user=self.student,
            organization=self.org,
            role=OrganizationRole.STUDENT,
        )

    def test_staff_sees_roles_as_read_only(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("organizations_admin:students", kwargs={"slug": self.org.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff")
        self.assertContains(response, "Student")
        self.assertNotContains(response, "name=\"role\"")
        self.assertNotContains(response, "student_role")

    def test_staff_cannot_change_a_member_role(self):
        self.client.force_login(self.staff)
        member = OrganizationMember.objects.get(
            user=self.student,
            organization=self.org,
        )

        response = self.client.post(
            reverse(
                "organizations_admin:student_role",
                kwargs={"slug": self.org.slug, "member_id": member.id},
            ),
            {"role": OrganizationRole.STAFF},
        )

        self.assertEqual(response.status_code, 403)
        member.refresh_from_db()
        self.assertEqual(member.role, OrganizationRole.STUDENT)
