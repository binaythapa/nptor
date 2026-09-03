from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.test import RequestFactory

from courses.services.permissions import can_create_course
from organizations.models.role import OrganizationRole


class CourseCreationAuthorizationTests(TestCase):
    def _user(self, *, superuser=False):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=superuser,
        )

    @patch("courses.services.permissions.get_active_membership")
    def test_student_role_cannot_create_course(self, get_active_membership):
        user = self._user()
        organization = object()
        get_active_membership.return_value = SimpleNamespace(
            role=OrganizationRole.STUDENT,
        )

        self.assertFalse(can_create_course(user, organization))
        get_active_membership.assert_called_once_with(user, organization)

    @patch("courses.services.permissions.get_active_membership")
    def test_staff_can_create_course_in_organization(self, get_active_membership):
        user = self._user()
        organization = object()
        get_active_membership.return_value = SimpleNamespace(
            role=OrganizationRole.STAFF,
        )

        self.assertTrue(can_create_course(user, organization))
        get_active_membership.assert_called_once_with(user, organization)

    def test_superuser_can_create_platform_course(self):
        user = self._user(superuser=True)

        self.assertTrue(can_create_course(user, None))

    @patch("courses.services.permissions.can_create_course", return_value=False)
    def test_course_creation_route_denies_unauthorized_user(self, can_create_course_mock):
        from courses import urls

        request = RequestFactory().post("/instructor/course/create/")
        request.user = self._user()
        request.active_org = object()

        # The route is wrapped by the authorization decorator; resolve the
        # wrapped callback directly so the test does not depend on the full
        # project URL configuration.
        callback = urls.urlpatterns[12].callback
        response = callback(request)

        self.assertEqual(response.status_code, 403)
        can_create_course_mock.assert_called_once_with(
            request.user,
            request.active_org,
        )
