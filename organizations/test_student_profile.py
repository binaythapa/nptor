from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from organizations.models import AcademicYear, ClassSection, ClassTeacher, Organization, OrganizationClass, OrganizationMember, OrganizationStudent, StudentEnrollment
from organizations.models.role import OrganizationRole
from organizations.services.students import get_organization_student, get_student_for_teacher, update_student_profile

User = get_user_model()


class StudentProfileTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Profile School", slug="profile-school", org_type=Organization.TYPE_SCHOOL)
        self.other_org = Organization.objects.create(name="Other School", slug="profile-other", org_type=Organization.TYPE_SCHOOL)
        self.student_user = User.objects.create_user(username="profile-student", email="student@example.com", password="password")
        self.admin = User.objects.create_user(username="profile-admin", password="password")
        self.teacher = User.objects.create_user(username="profile-teacher", password="password")
        OrganizationMember.objects.create(user=self.student_user, organization=self.org, role=OrganizationRole.STUDENT)
        OrganizationMember.objects.create(user=self.admin, organization=self.org, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.teacher, organization=self.org, role=OrganizationRole.STAFF)
        self.student = OrganizationStudent.objects.create(organization=self.org, user=self.student_user, student_id="S001")
        year = AcademicYear.objects.create(organization=self.org, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        klass = OrganizationClass.objects.create(organization=self.org, name="Grade 10")
        self.section = ClassSection.objects.create(organization=self.org, academic_year=year, class_group=klass, name="A")
        ClassTeacher.objects.create(organization=self.org, teacher=self.teacher, class_section=self.section, academic_year=year)
        StudentEnrollment.objects.create(student=self.student, academic_year=year, class_section=self.section)

    def test_student_can_view_and_update_own_profile(self):
        self.assertEqual(get_organization_student(self.student_user, self.org), self.student)
        update_student_profile(actor=self.student_user, organization=self.org, student=self.student, data={"first_name": "New", "guardian_name": "Parent"})
        self.student.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual(self.student.guardian_name, "Parent")
        self.assertEqual(self.student_user.first_name, "New")

    def test_student_cannot_update_enrollment_or_student_id(self):
        with self.assertRaises(PermissionDenied):
            update_student_profile(actor=self.student_user, organization=self.org, student=self.student, data={"student_id": "HACK"})

    def test_admin_can_view_and_edit_student_profile(self):
        update_student_profile(actor=self.admin, organization=self.org, student=self.student, data={"address": "New address"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.address, "New address")

    def test_teacher_can_view_only_students_in_assigned_class(self):
        self.assertEqual(get_student_for_teacher(actor=self.teacher, student_id=self.student.id, organization=self.org), self.student)
        other = User.objects.create_user(username="outside-student", password="password")
        OrganizationMember.objects.create(user=other, organization=self.org, role=OrganizationRole.STUDENT)
        other_student = OrganizationStudent.objects.create(organization=self.org, user=other)
        with self.assertRaises(PermissionDenied):
            get_student_for_teacher(actor=self.teacher, student_id=other_student.id, organization=self.org)

    def test_student_cannot_view_profile_from_another_organization(self):
        with self.assertRaises(PermissionDenied):
            get_organization_student(self.student_user, self.other_org)
