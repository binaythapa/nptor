from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from organizations.models import AcademicYear, ClassSection, ClassTeacher, Organization, OrganizationClass, OrganizationMember, OrganizationStudent, StudentEnrollment
from organizations.models.role import OrganizationRole
from organizations.services.enrollment import enroll_student, transfer_student

User = get_user_model()


class AcademicEnrollmentPermissionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Enrollment School", slug="enrollment-school", org_type=Organization.TYPE_SCHOOL)
        self.other_org = Organization.objects.create(name="Other", slug="enrollment-other", org_type=Organization.TYPE_SCHOOL)
        self.admin = User.objects.create_user(username="enrollment-admin", password="password")
        self.teacher = User.objects.create_user(username="enrollment-teacher", password="password")
        self.student_user = User.objects.create_user(username="enrollment-student", password="password")
        OrganizationMember.objects.create(user=self.admin, organization=self.org, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.teacher, organization=self.org, role=OrganizationRole.STAFF)
        OrganizationMember.objects.create(user=self.student_user, organization=self.org, role=OrganizationRole.STUDENT)
        self.student = OrganizationStudent.objects.create(organization=self.org, user=self.student_user)
        self.year = AcademicYear.objects.create(organization=self.org, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        self.klass = OrganizationClass.objects.create(organization=self.org, name="Grade 10")
        self.section = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=self.klass, name="A")
        self.other_section = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=self.klass, name="B")
        ClassTeacher.objects.create(organization=self.org, teacher=self.teacher, class_section=self.section, academic_year=self.year)

    def test_admin_can_enroll_existing_organization_student(self):
        enrollment = enroll_student(actor=self.admin, student=self.student, section=self.section)
        self.assertEqual(enrollment.class_section, self.section)

    def test_teacher_can_enroll_only_into_assigned_section(self):
        enrollment = enroll_student(actor=self.teacher, student=self.student, section=self.section)
        self.assertEqual(enrollment.class_section, self.section)
        with self.assertRaises(PermissionDenied):
            enroll_student(actor=self.teacher, student=self.student, section=self.other_section)

    def test_teacher_cannot_enroll_platform_user_without_student_record(self):
        user = User.objects.create_user(username="not-org-student", password="password")
        with self.assertRaises(Exception):
            enroll_student(actor=self.teacher, student=user, section=self.section)

    def test_cross_organization_enrollment_is_denied(self):
        other_user = User.objects.create_user(username="cross-org", password="password")
        OrganizationMember.objects.create(user=other_user, organization=self.other_org, role=OrganizationRole.STUDENT)
        other_student = OrganizationStudent.objects.create(organization=self.other_org, user=other_user)
        with self.assertRaises(Exception):
            enroll_student(actor=self.admin, student=other_student, section=self.section)

    def test_teacher_cannot_transfer_from_unassigned_source_class(self):
        enrollment = enroll_student(actor=self.admin, student=self.student, section=self.section)
        with self.assertRaises(PermissionDenied):
            transfer_student(actor=self.teacher, enrollment=enrollment, section=self.other_section)
