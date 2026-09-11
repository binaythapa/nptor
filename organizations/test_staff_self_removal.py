from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole


User = get_user_model()


class StaffSelfRemovalTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Self Removal School",
            slug="self-removal-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.staff = User.objects.create_user(
            username="self-removal-staff",
            email="self-removal-staff@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.staff,
            organization=self.org,
            role=OrganizationRole.STAFF,
        )

    def test_staff_cannot_remove_themselves(self):
        self.client.force_login(self.staff)
        member = OrganizationMember.objects.get(user=self.staff, organization=self.org)

        response = self.client.post(
            reverse(
                "organizations_admin:student_remove",
                kwargs={"slug": self.org.slug, "member_id": member.id},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            OrganizationMember.objects.filter(
                user=self.staff,
                organization=self.org,
                is_active=True,
            ).exists()
        )

    def test_staff_does_not_see_remove_action_for_their_own_membership(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse(
                "organizations_admin:students",
                kwargs={"slug": self.org.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "student_remove")
        self.assertNotContains(response, ">Remove</a>")
