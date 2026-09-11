from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from courses.models import Course
from courses.views.instructor_dashboard_view import instructor_dashboard
from organizations.models import Organization


class InstructorDashboardContextTests(TestCase):
    def test_my_courses_excludes_courses_already_shown_for_active_organization(self):
        user = get_user_model().objects.create_user(
            username="org-instructor",
            password="test-password",
        )
        organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
        )
        organization_course = Course.objects.create(
            title="Organization Course",
            description="Org course",
            level="beginner",
            owner_type=Course.OWNER_ORGANIZATION,
            organization=organization,
            created_by=user,
        )
        personal_course = Course.objects.create(
            title="Personal Course",
            description="Personal course",
            level="beginner",
            owner_type=Course.OWNER_PLATFORM,
            organization=None,
            created_by=user,
        )

        request = RequestFactory().get("/courses/instructor/dashboard/")
        request.user = user
        request.organization = organization

        with patch(
            "courses.views.instructor_dashboard_view.can_view_instructor_dashboard",
            return_value=True,
        ):
            response = instructor_dashboard(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context_data["organization_courses"]),
            [organization_course],
        )
        self.assertEqual(
            list(response.context_data["my_courses"]),
            [personal_course],
        )
