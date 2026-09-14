from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMember


class AssignmentStudentSearchUITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="school-admin",
            first_name="School",
            last_name="Admin",
            password="pass",
        )
        self.org = Organization.objects.create(name="School", slug="school")
        OrganizationMember.objects.create(
            user=self.admin,
            organization=self.org,
            role=OrganizationMember.ROLE_OWNER,
            is_active=True,
        )

        for username, first_name, last_name in (
            ("thapa.aarav", "Aarav", "Thapa"),
            ("thapa.ramesh", "Ramesh", "Thapa"),
            ("ananya.thapa", "Ananya", "Thapa"),
            ("sita.karki", "Sita", "Karki"),
        ):
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password="pass",
            )
            OrganizationMember.objects.create(
                user=user,
                organization=self.org,
                role=OrganizationMember.ROLE_STUDENT,
                is_active=True,
            )

        self.client.login(username="school-admin", password="pass")

    def test_assignment_form_has_searchable_student_picker(self):
        response = self.client.get(
            reverse(
                "organizations_admin:assignment_create",
                kwargs={"slug": self.org.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="student_search"')
        self.assertContains(response, 'id="student_results"')
        self.assertContains(response, 'name="student_id"')
        self.assertContains(response, "thapa.aarav")
        self.assertContains(response, "thapa.ramesh")
        self.assertContains(response, "ananya.thapa")
        self.assertContains(response, "sita.karki")
        self.assertContains(response, "startsWith")
