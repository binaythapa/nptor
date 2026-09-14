from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import Organization, OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


User = get_user_model()


class OrganizationAdminStudentProfileTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="org-admin",
            email="admin@example.com",
            password="password",
        )
        self.student_user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="password",
        )
        self.organization = Organization.objects.create(
            name="Example School",
            slug="example-school",
            org_type=Organization.TYPE_SCHOOL,
            created_by=self.admin,
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationRole.ORG_ADMIN,
            is_active=True,
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.student_user,
            role=OrganizationRole.STUDENT,
            is_active=True,
        )
        self.student = OrganizationStudent.objects.create(
            organization=self.organization,
            user=self.student_user,
            student_id="ST-001",
            admission_no="ADM-001",
            status=OrganizationStudent.STATUS_ACTIVE,
            joined_date=date(2026, 1, 10),
        )

    def test_admin_can_open_student_profile_and_edit_organization_fields(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "organizations_public:student_profile_admin",
                kwargs={"slug": self.organization.slug, "student_id": self.student.id},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ST-001")
        self.assertContains(response, "ADM-001")

        response = self.client.post(
            reverse(
                "organizations_public:student_profile_admin_edit",
                kwargs={"slug": self.organization.slug, "student_id": self.student.id},
            ),
            data={
                "first_name": "Updated",
                "last_name": "Student",
                "email": self.student_user.email,
                "contact_phone": "9800000000",
                "student_id": "ST-009",
                "admission_no": "ADM-009",
                "status": OrganizationStudent.STATUS_ACTIVE,
                "joined_date": "2026-02-01",
                "date_of_birth": "2010-05-12",
                "guardian_name": "Guardian Name",
                "guardian_phone": "9811111111",
                "address": "New Address",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "organizations_public:student_profile_admin",
                kwargs={"slug": self.organization.slug, "student_id": self.student.id},
            ),
        )
        self.student.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual(self.student.student_id, "ST-009")
        self.assertEqual(self.student.admission_no, "ADM-009")
        self.assertEqual(self.student.address, "New Address")
        self.assertEqual(self.student_user.first_name, "Updated")
        self.assertEqual(self.student_user.last_name, "Student")

    def test_non_admin_cannot_edit_student_profile(self):
        self.client.force_login(self.student_user)
        response = self.client.get(
            reverse(
                "organizations_public:student_profile_admin_edit",
                kwargs={"slug": self.organization.slug, "student_id": self.student.id},
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_role_change_to_staff_deactivates_student_profile(self):
        self.client.force_login(self.admin)
        member = OrganizationMember.objects.get(
            user=self.student_user,
            organization=self.organization,
        )
        response = self.client.post(
            reverse(
                "organizations_admin:student_role",
                kwargs={"slug": self.organization.slug, "member_id": member.id},
            ),
            data={"role": OrganizationRole.STAFF},
        )
        self.assertRedirects(
            response,
            reverse("organizations_admin:students", kwargs={"slug": self.organization.slug}),
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, OrganizationStudent.STATUS_INACTIVE)

    def test_profile_form_contains_admin_owned_student_fields(self):
        from organizations.forms.student import OrganizationStudentAdminProfileForm

        form = OrganizationStudentAdminProfileForm(instance=self.student)
        for field in ("student_id", "admission_no", "status", "joined_date"):
            self.assertIn(field, form.fields)
