from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organizations.models import (
    AcademicYear,
    ClassSection,
    Organization,
    OrganizationClass,
    OrganizationMember,
    OrganizationStudent,
    StudentEnrollment,
)
from organizations.models.role import OrganizationRole


class AdminStudentEnrollmentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="admin", password="pass")
        self.student_user = User.objects.create_user(username="student", password="pass", first_name="Test", last_name="Student")
        self.org = Organization.objects.create(name="School", slug="school")
        OrganizationMember.objects.create(user=self.user, organization=self.org, role=OrganizationRole.OWNER, is_active=True)
        OrganizationMember.objects.create(user=self.student_user, organization=self.org, role=OrganizationRole.STUDENT, is_active=True)
        self.student = OrganizationStudent.objects.create(organization=self.org, user=self.student_user, status=OrganizationStudent.STATUS_ACTIVE)
        self.year = AcademicYear.objects.create(organization=self.org, name="2026-2027", start_date="2026-04-01", end_date="2027-03-31", is_current=True)
        self.klass = OrganizationClass.objects.create(organization=self.org, name="Grade 10")
        self.section_a = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=self.klass, name="A")
        self.section_b = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=self.klass, name="B")
        self.client.login(username="admin", password="pass")

    def test_enrollment_page_creates_enrollment(self):
        response = self.client.post(
            reverse("organizations_admin:student_enroll", kwargs={"slug": self.org.slug, "student_id": self.student.id}),
            {"academic_year": self.year.id, "class_section": self.section_a.id, "roll_number": "15"},
        )
        self.assertRedirects(response, reverse("organizations_admin:student_detail", kwargs={"slug": self.org.slug, "student_id": self.student.id}))
        enrollment = StudentEnrollment.objects.get(student=self.student)
        self.assertEqual(enrollment.class_section_id, self.section_a.id)
        self.assertEqual(enrollment.roll_number, "15")

    def test_detail_shows_current_and_history(self):
        enrollment = StudentEnrollment.objects.create(student=self.student, academic_year=self.year, class_section=self.section_a, roll_number="15")
        response = self.client.get(reverse("organizations_admin:student_detail", kwargs={"slug": self.org.slug, "student_id": self.student.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2026-2027")
        self.assertContains(response, "Grade 10")
        self.assertContains(response, "15")
        self.assertContains(response, "Active")

    def test_transfer_creates_history_and_new_active_enrollment(self):
        enrollment = StudentEnrollment.objects.create(student=self.student, academic_year=self.year, class_section=self.section_a, roll_number="15")
        response = self.client.post(
            reverse("organizations_admin:student_enrollment_transfer", kwargs={"slug": self.org.slug, "student_id": self.student.id, "enrollment_id": enrollment.id}),
            {"class_section": self.section_b.id, "roll_number": "20"},
        )
        self.assertRedirects(response, reverse("organizations_admin:student_detail", kwargs={"slug": self.org.slug, "student_id": self.student.id}))
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, StudentEnrollment.STATUS_TRANSFERRED)
        current = StudentEnrollment.objects.get(student=self.student, status=StudentEnrollment.STATUS_ACTIVE)
        self.assertEqual(current.class_section_id, self.section_b.id)
        self.assertEqual(current.roll_number, "20")

    def test_enrollment_is_organization_scoped(self):
        other = Organization.objects.create(name="Other School", slug="other-school")
        response = self.client.get(reverse("organizations_admin:student_enroll", kwargs={"slug": other.slug, "student_id": self.student.id}))
        self.assertEqual(response.status_code, 404)
