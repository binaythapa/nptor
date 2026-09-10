from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from organizations.models import AcademicYear, ClassSection, Organization, OrganizationClass, OrganizationMember, OrganizationStudent, StudentEnrollment
from organizations.models.role import OrganizationRole
from organizations.services.enrollment import enroll_student

User = get_user_model()


class StudentAcademicModelTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="School A", slug="academic-a", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="School B", slug="academic-b", org_type=Organization.TYPE_SCHOOL)
        self.user = User.objects.create_user(username="academic-student", password="password")
        self.admin = User.objects.create_user(username="academic-admin", password="password")
        OrganizationMember.objects.create(user=self.user, organization=self.org_a, role=OrganizationRole.STUDENT)
        OrganizationMember.objects.create(user=self.user, organization=self.org_b, role=OrganizationRole.STUDENT)
        OrganizationMember.objects.create(user=self.admin, organization=self.org_a, role=OrganizationRole.ORG_ADMIN)

    def test_student_identity_is_unique_per_organization(self):
        OrganizationStudent.objects.create(organization=self.org_a, user=self.user)
        OrganizationStudent.objects.create(organization=self.org_b, user=self.user)
        with self.assertRaises(Exception):
            OrganizationStudent.objects.create(organization=self.org_a, user=self.user)

    def test_active_enrollment_is_unique_for_an_academic_year(self):
        student = OrganizationStudent.objects.create(organization=self.org_a, user=self.user)
        year = AcademicYear.objects.create(organization=self.org_a, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        klass = OrganizationClass.objects.create(organization=self.org_a, name="Grade 10")
        section = ClassSection.objects.create(organization=self.org_a, academic_year=year, class_group=klass, name="A")
        enroll_student(actor=self.admin, student=student, section=section)
        with self.assertRaises(ValidationError):
            enroll_student(actor=self.admin, student=student, section=ClassSection.objects.create(organization=self.org_a, academic_year=year, class_group=klass, name="B"))

    def test_class_section_and_student_must_share_organization(self):
        student = OrganizationStudent.objects.create(organization=self.org_a, user=self.user)
        year_b = AcademicYear.objects.create(organization=self.org_b, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        klass_b = OrganizationClass.objects.create(organization=self.org_b, name="Grade 10")
        section_b = ClassSection.objects.create(organization=self.org_b, academic_year=year_b, class_group=klass_b, name="A")
        enrollment = StudentEnrollment(student=student, academic_year=year_b, class_section=section_b)
        with self.assertRaises(ValidationError):
            enrollment.full_clean()

    def test_historical_enrollment_can_be_retained_after_transfer(self):
        student = OrganizationStudent.objects.create(organization=self.org_a, user=self.user)
        year = AcademicYear.objects.create(organization=self.org_a, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        klass = OrganizationClass.objects.create(organization=self.org_a, name="Grade 10")
        section_a = ClassSection.objects.create(organization=self.org_a, academic_year=year, class_group=klass, name="A")
        section_b = ClassSection.objects.create(organization=self.org_a, academic_year=year, class_group=klass, name="B")
        old = StudentEnrollment.objects.create(student=student, academic_year=year, class_section=section_a, status=StudentEnrollment.STATUS_TRANSFERRED)
        current = StudentEnrollment.objects.create(student=student, academic_year=year, class_section=section_b)
        self.assertEqual(old.status, StudentEnrollment.STATUS_TRANSFERRED)
        self.assertEqual(current.status, StudentEnrollment.STATUS_ACTIVE)
