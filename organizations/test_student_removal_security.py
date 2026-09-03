from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from organizations.models.access import ResourceAccess
from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.services.assignments import assign_resource


User = get_user_model()


class StudentRemovalAccessRegressionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Removal Security School",
            slug="removal-security-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="removal-admin",
            email="removal-admin@example.com",
            password="password",
        )
        self.student = User.objects.create_user(
            username="removal-student",
            email="removal-student@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=self.admin,
            organization=self.organization,
            role=OrganizationRole.ORG_ADMIN,
            is_active=True,
        )
        self.member = OrganizationMember.objects.create(
            user=self.student,
            organization=self.organization,
            role=OrganizationRole.STUDENT,
            is_active=True,
        )
        self.course = Course.objects.create(
            title="Assigned Course",
        )
        self.assignment_result = assign_resource(
            actor=self.admin,
            organization=self.organization,
            student=self.student,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            resource_id=self.course.id,
        )

    def test_removing_student_revokes_organization_assignment_and_access(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "organizations_admin:student_remove",
                kwargs={
                    "slug": self.organization.slug,
                    "member_id": self.member.id,
                },
            )
        )

        self.assertEqual(response.status_code, 302)

        assignment = ResourceAssignment.objects.get(
            id=self.assignment_result.assignment.id,
        )
        access = ResourceAccess.objects.get(
            id=self.assignment_result.access.id,
        )

        self.assertFalse(
            OrganizationMember.objects.filter(
                id=self.member.id,
            ).exists()
        )
        self.assertFalse(assignment.is_active)
        self.assertEqual(
            assignment.status,
            ResourceAssignment.STATUS_REVOKED,
        )
        self.assertEqual(
            assignment.revoked_by_id,
            self.admin.id,
        )
        self.assertIsNotNone(assignment.revoked_at)
        self.assertFalse(access.is_active)
        self.assertIsNotNone(access.revoked_at)
