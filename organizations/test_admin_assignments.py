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
    def _create_staff_and_student(self):
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
        return organization, staff, student

    def test_assignment_list_renders_without_invalid_related_lookup(self):
        organization, staff, student = self._create_staff_and_student()
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

    def test_assignment_list_filters_by_search_query(self):
        organization, staff, student = self._create_staff_and_student()
        matching_course = Course.objects.create(title="Accounting Basics")
        other_course = Course.objects.create(title="Physics Fundamentals")
        ResourceAssignment.objects.create(
            organization=organization,
            student=student,
            assigned_by=staff,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            course=matching_course,
        )
        ResourceAssignment.objects.create(
            organization=organization,
            student=student,
            assigned_by=staff,
            resource_type=ResourceAssignment.RESOURCE_COURSE,
            course=other_course,
        )

        request = RequestFactory().get(
            f"/org/{organization.slug}/admin/assignments/",
            {"q": "Accounting"},
        )
        request.user = staff
        request.organization = organization

        response = org_assignments.__wrapped__(
            request,
            organization.slug,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accounting Basics")
        self.assertNotContains(response, "Physics Fundamentals")
        self.assertContains(response, "value=\"Accounting\"")
