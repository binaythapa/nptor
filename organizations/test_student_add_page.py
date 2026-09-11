from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole


User = get_user_model()


class StudentAddPageTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Add Student School",
            slug="add-student-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.admin = User.objects.create_user(username="add-student-admin", email="add-student-admin@example.com", password="password")
        self.staff = User.objects.create_user(username="add-student-staff", email="add-student-staff@example.com", password="password")
        OrganizationMember.objects.create(user=self.admin, organization=self.organization, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.staff, organization=self.organization, role=OrganizationRole.STAFF)

    def _url(self):
        return reverse("organizations_admin:student_add", kwargs={"slug": self.organization.slug})

    def test_admin_can_open_add_student_page_with_get(self):
        self.client.force_login(self.admin)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Student")
        self.assertContains(response, 'value="student"')
        self.assertContains(response, 'value="staff"')

    def test_staff_can_open_add_student_page_with_get_but_only_student_role(self):
        self.client.force_login(self.staff)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Student")
        self.assertContains(response, 'value="student"')
        self.assertNotContains(response, 'value="staff"')

    def test_add_student_post_still_creates_membership(self):
        new_student = User.objects.create_user(username="new-add-student", email="new-student@example.com", password="password")
        self.client.force_login(self.admin)
        response = self.client.post(self._url(), {"email": new_student.email, "role": OrganizationRole.STUDENT})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrganizationMember.objects.filter(organization=self.organization, user=new_student).exists())
