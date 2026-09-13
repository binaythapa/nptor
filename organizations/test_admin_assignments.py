from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from organizations.models.assignment import ResourceAssignment
from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.views.admin.assignments import org_assignments
from courses.models import Course


User = get_user_model()


class OrganizationAssignmentAdminViewTests(TestCase):
    def test_assignment_list_renders_without_invalid_related_lookup(self):
        organization = Organization.objects.create(
            name="Test School",
            slug="test-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password",
        )
        student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="password",
        )
        OrganizationMember.objects.create(
            user=staff,
            organization=organization,
            role=OrganizationRole.STAFF,
        )
        OrganizationMember.objects.create(
            user=student,
            organization=organization,
            role=OrganizationRole.STUDENT,
        )
        course = Course.objects.create(title="Test Course")
        ResourceAssignment.objects.create(
            organization=organization,
            student=student,
            assigned_by=staff,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            course=course,
        )

        request = RequestFactory().get(
            f"/org/{organization.slug}/admin/assignments/"
        )
        request.user = staff
        request.organization = organization

        response = org_assignments.__wrapped__(
            request,
            organization.slug,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
