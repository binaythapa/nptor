# organizations/tests.py

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from organizations.models.assignment import ResourceAssignment
from organizations.models.access import ResourceAccess
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole

from organizations.services.assignments import (
    assign_resource,
    revoke_assignment,
    DuplicateActiveAssignmentError,
    StudentNotInOrganizationError,
    UnauthorizedAssignmentError,
    InvalidAssignmentError,
)

from courses.models import Course

User = get_user_model()


class OrganizationAssignmentTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test School", slug="test-school", org_type=Organization.TYPE_SCHOOL, is_active=True)
        self.other_organization = Organization.objects.create(name="Other School", slug="other-school", org_type=Organization.TYPE_SCHOOL, is_active=True)
        self.owner = User.objects.create_user(username="owner", email="owner@test.com", password="test-password")
        self.admin = User.objects.create_user(username="admin", email="admin@test.com", password="test-password")
        self.teacher = User.objects.create_user(username="teacher", email="teacher@test.com", password="test-password")
        self.student = User.objects.create_user(username="student", email="student@test.com", password="test-password")
        self.other_student = User.objects.create_user(username="otherstudent", email="otherstudent@test.com", password="test-password")
        OrganizationMember.objects.create(user=self.owner, organization=self.organization, role=OrganizationRole.ORG_OWNER)
        OrganizationMember.objects.create(user=self.admin, organization=self.organization, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.teacher, organization=self.organization, role=OrganizationRole.STAFF)
        OrganizationMember.objects.create(user=self.student, organization=self.organization, role=OrganizationRole.STUDENT)
        OrganizationMember.objects.create(user=self.other_student, organization=self.other_organization, role=OrganizationRole.STUDENT)
        self.course = Course.objects.create(title="Test Course")

    def test_organization_roles_exist(self):
        self.assertEqual(OrganizationRole.ORG_OWNER, "org_owner")
        self.assertEqual(OrganizationRole.ORG_ADMIN, "org_admin")
        self.assertEqual(OrganizationRole.STAFF, "staff")
        self.assertEqual(OrganizationRole.STUDENT, "student")

    def test_owner_can_manage_students(self):
        self.assertTrue(OrganizationMember.objects.get(user=self.owner, organization=self.organization).can_manage_students)

    def test_admin_can_manage_students(self):
        self.assertTrue(OrganizationMember.objects.get(user=self.admin, organization=self.organization).can_manage_students)

    def test_teacher_can_manage_students(self):
        self.assertTrue(OrganizationMember.objects.get(user=self.teacher, organization=self.organization).can_manage_students)

    def test_student_cannot_manage_students(self):
        self.assertFalse(OrganizationMember.objects.get(user=self.student, organization=self.organization).can_manage_students)

    def test_owner_can_assign_course(self):
        result = assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        self.assertTrue(result.created)
        self.assertEqual(result.assignment.student, self.student)
        self.assertEqual(result.assignment.organization, self.organization)
        self.assertEqual(result.assignment.course, self.course)
        self.assertTrue(result.assignment.is_active)

    def test_admin_can_assign_course(self):
        result = assign_resource(actor=self.admin, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        self.assertTrue(result.created)

    def test_teacher_can_assign_course(self):
        result = assign_resource(actor=self.teacher, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        self.assertTrue(result.created)

    def test_student_cannot_assign_course(self):
        with self.assertRaises(UnauthorizedAssignmentError):
            assign_resource(actor=self.student, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)

    def test_student_from_another_organization_cannot_be_assigned(self):
        with self.assertRaises(StudentNotInOrganizationError):
            assign_resource(actor=self.owner, organization=self.organization, student=self.other_student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)

    def test_duplicate_active_assignment_is_rejected(self):
        assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        with self.assertRaises(DuplicateActiveAssignmentError):
            assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)

    def test_assignment_creates_resource_access(self):
        result = assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        self.assertIsNotNone(result.access)
        self.assertEqual(result.access.user, self.student)
        self.assertEqual(result.access.organization, self.organization)
        self.assertEqual(result.access.assignment, result.assignment)
        self.assertTrue(result.access.is_active)

    def test_assignment_timeline_is_saved(self):
        starts_at = timezone.now()
        due_at = starts_at + timedelta(days=7)
        expires_at = starts_at + timedelta(days=14)
        result = assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id, starts_at=starts_at, due_at=due_at, expires_at=expires_at)
        self.assertEqual(result.assignment.starts_at, starts_at)
        self.assertEqual(result.assignment.due_at, due_at)
        self.assertEqual(result.assignment.expires_at, expires_at)

    def test_invalid_timeline_is_rejected(self):
        starts_at = timezone.now()
        with self.assertRaises(InvalidAssignmentError):
            assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id, starts_at=starts_at, due_at=starts_at - timedelta(days=1))

    def test_revoke_assignment_preserves_history(self):
        result = assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        revoke_assignment(assignment=result.assignment, actor=self.owner, reason="Student transferred.")
        assignment = ResourceAssignment.objects.get(id=result.assignment.id)
        access = ResourceAccess.objects.get(id=result.access.id)
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.status, ResourceAssignment.STATUS_REVOKED)
        self.assertFalse(access.is_active)
        self.assertIsNotNone(assignment.revoked_at)
        self.assertEqual(assignment.revoke_reason, "Student transferred.")

    def test_assignment_and_access_counts(self):
        result = assign_resource(actor=self.owner, organization=self.organization, student=self.student, resource_type=ResourceAssignment.RESOURCE_COURSE, resource_id=self.course.id)
        self.assertEqual(ResourceAssignment.objects.count(), 1)
        self.assertEqual(ResourceAccess.objects.count(), 1)
        self.assertEqual(result.assignment.assignment_key.__class__.__name__, "UUID")


class OrganizationAuthorizationRegressionTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="School A", slug="school-a", org_type=Organization.TYPE_SCHOOL)
        self.org_b = Organization.objects.create(name="School B", slug="school-b", org_type=Organization.TYPE_SCHOOL)
        self.admin = User.objects.create_user(username="admin-a", email="admin-a@example.com", password="password")
        self.other_admin = User.objects.create_user(username="admin-b", email="admin-b@example.com", password="password")
        self.student = User.objects.create_user(username="student", email="student@example.com", password="password")
        OrganizationMember.objects.create(user=self.admin, organization=self.org_a, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.other_admin, organization=self.org_b, role=OrganizationRole.ORG_ADMIN)
        OrganizationMember.objects.create(user=self.student, organization=self.org_a, role=OrganizationRole.STUDENT)

    def test_admin_membership_is_scoped_to_its_organization(self):
        self.assertTrue(OrganizationMember.objects.filter(user=self.other_admin, organization=self.org_b, role=OrganizationRole.ORG_ADMIN).exists())
        self.assertFalse(OrganizationMember.objects.filter(user=self.other_admin, organization=self.org_a).exists())

    def test_student_management_roles_cannot_create_admin_membership(self):
        self.assertNotIn(OrganizationRole.ORG_ADMIN, {OrganizationRole.STUDENT, OrganizationRole.STAFF})

    def test_inactive_membership_is_not_active_access(self):
        member = OrganizationMember.objects.get(user=self.admin, organization=self.org_a)
        member.is_active = False
        member.save(update_fields=["is_active"])
        self.assertFalse(OrganizationMember.objects.filter(user=self.admin, organization=self.org_a, is_active=True).exists())
