from django.contrib.auth import get_user_model
from django.test import TestCase

from courses.models import Course
from organizations.models import AcademicYear, ClassResourceAssignment, ClassSection, ClassTeacher, Organization, OrganizationClass, OrganizationMember, OrganizationStudent, StudentEnrollment
from organizations.models.role import OrganizationRole
from organizations.services.class_assignments import assign_class_resource, student_has_class_resource_access

User = get_user_model()


class ClassResourceAssignmentTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Class Assignment School", slug="class-assignment-school", org_type=Organization.TYPE_SCHOOL)
        self.teacher = User.objects.create_user(username="class-teacher", password="password")
        self.student_user = User.objects.create_user(username="class-student", password="password")
        OrganizationMember.objects.create(user=self.teacher, organization=self.org, role=OrganizationRole.STAFF)
        OrganizationMember.objects.create(user=self.student_user, organization=self.org, role=OrganizationRole.STUDENT)
        self.student = OrganizationStudent.objects.create(organization=self.org, user=self.student_user)
        self.year = AcademicYear.objects.create(organization=self.org, name="2026/27", start_date="2026-04-01", end_date="2027-03-31")
        klass = OrganizationClass.objects.create(organization=self.org, name="Grade 9")
        self.section = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=klass, name="A")
        self.other_section = ClassSection.objects.create(organization=self.org, academic_year=self.year, class_group=klass, name="B")
        ClassTeacher.objects.create(organization=self.org, teacher=self.teacher, class_section=self.section, academic_year=self.year)
        StudentEnrollment.objects.create(student=self.student, academic_year=self.year, class_section=self.section)
        self.course = Course.objects.create(title="Mathematics", organization=self.org, owner_type=Course.OWNER_ORGANIZATION)

    def test_teacher_can_assign_course_to_assigned_class(self):
        assignment = assign_class_resource(actor=self.teacher, section=self.section, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course)
        self.assertEqual(assignment.class_section, self.section)

    def test_teacher_cannot_assign_resource_to_unassigned_class(self):
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            assign_class_resource(actor=self.teacher, section=self.other_section, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course)

    def test_enrolled_student_inherits_class_resource_access(self):
        assign_class_resource(actor=self.teacher, section=self.section, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course)
        self.assertTrue(student_has_class_resource_access(student=self.student_user, organization=self.org, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course))

    def test_student_transferred_out_of_class_loses_class_assignment_access(self):
        assign_class_resource(actor=self.teacher, section=self.section, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course)
        enrollment = self.student.enrollments.get()
        enrollment.status = StudentEnrollment.STATUS_TRANSFERRED
        enrollment.save(update_fields=["status"])
        self.assertFalse(student_has_class_resource_access(student=self.student_user, organization=self.org, resource_type=ClassResourceAssignment.RESOURCE_COURSE, resource=self.course))
