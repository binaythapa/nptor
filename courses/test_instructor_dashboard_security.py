from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.test import RequestFactory

from courses.services.permissions import (
    can_view_instructor_dashboard,
    instructor_dashboard_access_required,
)


class InstructorDashboardAuthorizationTests(TestCase):
    def _user(self, *, authenticated=True, superuser=False):
        return SimpleNamespace(
            is_authenticated=authenticated,
            is_superuser=superuser,
            is_staff=False,
        )

    @patch("courses.services.permissions.get_active_membership")
    def test_student_cannot_view_organization_instructor_dashboard(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        get_active_membership.return_value = SimpleNamespace(role="student")

        with patch(
            "courses.services.permissions.OrganizationRole.teaching_roles",
            return_value={"staff", "org_admin", "org_owner"},
        ):
            self.assertFalse(
                can_view_instructor_dashboard(user, organization)
            )

    @patch("courses.services.permissions.get_active_membership")
    def test_teacher_can_view_organization_instructor_dashboard(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        get_active_membership.return_value = SimpleNamespace(role="staff")

        with patch(
            "courses.services.permissions.OrganizationRole.teaching_roles",
            return_value={"staff", "org_admin", "org_owner"},
        ):
            self.assertTrue(
                can_view_instructor_dashboard(user, organization)
            )

    def test_unauthenticated_user_cannot_view_instructor_dashboard(self):
        self.assertFalse(
            can_view_instructor_dashboard(self._user(authenticated=False), object())
        )

    @patch("courses.services.permissions.can_view_instructor_dashboard", return_value=False)
    def test_dashboard_decorator_blocks_non_teaching_active_org_member(
        self,
        can_view,
    ):
        request = RequestFactory().get("/courses/instructor/dashboard/")
        request.user = self._user()
        request.active_org = object()

        view = instructor_dashboard_access_required(lambda request: "allowed")
        response = view(request)

        self.assertEqual(response.status_code, 403)
        can_view.assert_called_once_with(request.user, request.active_org)

    @patch("courses.services.permissions.can_view_instructor_dashboard", return_value=True)
    def test_dashboard_decorator_exposes_authorized_active_org_to_view(
        self,
        can_view,
    ):
        request = RequestFactory().get("/courses/instructor/dashboard/")
        request.user = self._user()
        request.active_org = object()

        view = instructor_dashboard_access_required(
            lambda request: request.organization
        )
        response = view(request)

        self.assertIs(response, request.active_org)
        can_view.assert_called_once_with(request.user, request.active_org)
