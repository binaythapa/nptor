from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from courses.models import Course
from organizations.models import OrganizationMember, OrganizationStudent
from organizations.models.assignment import ResourceAssignment
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.services.assignments import assign_resource
from organizations.services.students import get_student_for_teacher, update_student_profile


User = get_user_model()


class StaffAllStudentAccessTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Access School",
            slug="access-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher-access",
            email="teacher-access@example.com",
            password="password",
        )
        self.student_a = User.objects.create_user(
            username="student-a",
            email="student-a@example.com",
            password="password",
        )
        self.student_b = User.objects.create_user(
            username="student-b",
            email="student-b@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.teacher,
            organization=self.organization,
            role=OrganizationRole.STAFF,
        )
        for student in (self.student_a, self.student_b):
            OrganizationMember.objects.create(
                user=student,
                organization=self.organization,
                role=OrganizationRole.STUDENT,
            )
            OrganizationStudent.objects.create(
                user=student,
                organization=self.organization,
                status=OrganizationStudent.STATUS_ACTIVE,
            )
        self.course = Course.objects.create(title="Access Course")

    def test_staff_can_view_any_organization_student(self):
        record = OrganizationStudent.objects.get(user=self.student_b)
        result = get_student_for_teacher(
            actor=self.teacher,
            student_id=record.id,
            organization=self.organization,
        )
        self.assertEqual(result, record)

    def test_staff_can_assign_course_to_any_organization_student(self):
        assign_resource(
            actor=self.teacher,
            organization=self.organization,
            student=self.student_b,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            resource_id=self.course.id,
        )
        self.assertTrue(
            ResourceAssignment.objects.filter(
                organization=self.organization,
                student=self.student_b,
                course=self.course,
                is_active=True,
            ).exists()
        )

    def test_staff_cannot_edit_student_profile(self):
        record = OrganizationStudent.objects.get(user=self.student_b)
        with self.assertRaises(PermissionDenied):
            update_student_profile(
                actor=self.teacher,
                organization=self.organization,
                student=record,
                data={"address": "New address"},
            )
