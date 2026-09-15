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
        update_student_profile(actor=self.student_user, organization=self.org, student=self.student,
                               data={"first_name": "New", "guardian_name": "Parent", "contact_phone": "+977-9800000000"})
        self.student.refresh_from_db()
        self.student_user.refresh_from_db()
        self.assertEqual(self.student.guardian_name, "Parent")
        self.assertEqual(self.student_user.first_name, "New")
        self.assertEqual(str(self.student_user.profile.phone), "+977-9800000000")

    def test_student_cannot_update_enrollment_or_student_id(self):
        with self.assertRaises(PermissionDenied):
            update_student_profile(actor=self.student_user, organization=self.org, student=self.student, data={"student_id": "HACK"})

    def test_admin_can_view_and_edit_student_profile(self):
        update_student_profile(actor=self.admin, organization=self.org, student=self.student, data={"address": "New address"})
        self.student.refresh_from_db()
        self.assertEqual(self.student.address, "New address")

    def test_staff_can_view_organization_students(self):
        self.assertEqual(get_student_for_teacher(actor=self.teacher, student_id=self.student.id, organization=self.org), self.student)
        other = User.objects.create_user(username="outside-student", password="password")
        OrganizationMember.objects.create(user=other, organization=self.org, role=OrganizationRole.STUDENT)
        other_student = OrganizationStudent.objects.create(organization=self.org, user=other)
        self.assertEqual(get_student_for_teacher(actor=self.teacher, student_id=other_student.id, organization=self.org), other_student)

    def test_student_cannot_view_profile_from_another_organization(self):
        with self.assertRaises(PermissionDenied):
            get_organization_student(self.student_user, self.other_org)

    def test_student_profile_is_organization_specific(self):
        OrganizationMember.objects.create(user=self.student_user, organization=self.other_org, role=OrganizationRole.STUDENT)
        other_profile = OrganizationStudent.objects.create(organization=self.other_org, user=self.student_user, student_id="OTHER-001", guardian_name="Other Guardian")
        self.assertEqual(get_organization_student(self.student_user, self.org), self.student)
        self.assertEqual(get_organization_student(self.student_user, self.other_org), other_profile)

    def test_adding_student_membership_provisions_profile(self):
        new_student = User.objects.create_user(username="new-student", email="new.student@example.com", password="password")
        self.client.force_login(self.admin)
        response = self.client.post(f"/org/{self.org.slug}/admin/students/add/", {"email": new_student.email, "role": OrganizationRole.STUDENT})
        self.assertEqual(response.status_code, 302)
        profile = OrganizationStudent.objects.get(organization=self.org, user=new_student)
        self.assertEqual(profile.status, OrganizationStudent.STATUS_ACTIVE)
        self.assertIsNotNone(profile.joined_date)

    def test_readding_student_does_not_replace_existing_profile(self):
        self.client.force_login(self.admin)
        self.client.post(f"/org/{self.org.slug}/admin/students/add/", {"email": self.student_user.email, "role": OrganizationRole.STUDENT})
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_id, "S001")

    def test_existing_student_membership_gets_profile_on_first_access(self):
        legacy_user = User.objects.create_user(username="legacy-student", email="legacy@example.com", password="password")
        OrganizationMember.objects.create(user=legacy_user, organization=self.org, role=OrganizationRole.STUDENT)
        self.assertFalse(OrganizationStudent.objects.filter(user=legacy_user, organization=self.org).exists())
        profile = get_organization_student(legacy_user, self.org)
        self.assertEqual(profile.user, legacy_user)
        self.assertEqual(profile.organization, self.org)
        self.assertEqual(profile.status, OrganizationStudent.STATUS_ACTIVE)

    def test_student_workspace_surfaces_my_profile(self):
        self.client.force_login(self.student_user)
        response = self.client.get(f"/org/{self.org.slug}/workspace/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Profile")
        self.assertContains(response, f"/org/{self.org.slug}/student-profile/")

    def test_global_profile_surfaces_organization_account(self):
        self.client.force_login(self.student_user)
        response = self.client.get("/quiz/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization Accounts")
        self.assertContains(response, self.org.name)
        self.assertContains(response, "Student")
        self.assertContains(response, self.student.student_id)
        self.assertContains(response, f"/org/{self.org.slug}/student-profile/")
