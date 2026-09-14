from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from organizations.forms.student import OrganizationStudentAdminProfileForm
from organizations.models import Organization, OrganizationMember, OrganizationStudent
from organizations.models.role import OrganizationRole


class OrganizationAdminStudentDetailTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="org-admin-detail",
            email="org-admin-detail@example.com",
            password="testpass123",
        )
        self.student_user = User.objects.create_user(
            username="student-detail",
            email="student-detail@example.com",
            password="testpass123",
        )
        self.organization = Organization.objects.create(
            name="Detail School",
            slug="detail-school",
        )
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.admin,
            role=OrganizationRole.ADMIN,
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
            student_id="STU-1001",
            admission_no="ADM-2026-01",
            status=OrganizationStudent.STATUS_ACTIVE,
        )
        self.client.force_login(self.admin)

    def test_student_detail_uses_admin_route_and_template(self):
        response = self.client.get(
            reverse(
                "organizations_admin:student_detail",
                kwargs={
                    "slug": self.organization.slug,
                    "student_id": self.student.id,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "organizations/admin/students/detail.html")
        self.assertContains(response, "STU-1001")
        self.assertContains(response, "ADM-2026-01")
        self.assertContains(response, "Organization Admin")

    def test_student_detail_is_organization_scoped(self):
        other_org = Organization.objects.create(
            name="Other School",
            slug="other-school",
        )
        response = self.client.get(
            reverse(
                "organizations_admin:student_detail",
                kwargs={
                    "slug": other_org.slug,
                    "student_id": self.student.id,
                },
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_student_form_uses_bulma_form_widgets(self):
        form = OrganizationStudentAdminProfileForm(instance=self.student)

        for field_name in (
            "first_name",
            "last_name",
            "email",
            "contact_phone",
            "student_id",
            "admission_no",
            "joined_date",
            "date_of_birth",
            "guardian_name",
            "guardian_phone",
        ):
            self.assertIn("input", form.fields[field_name].widget.attrs.get("class", ""))

        self.assertEqual(form.fields["status"].widget.attrs.get("class"), "bulma-select")
        self.assertEqual(form.fields["address"].widget.attrs.get("class"), "textarea")
