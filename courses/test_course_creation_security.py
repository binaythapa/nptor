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

    @patch("courses.views.instructor_views.can_create_course", return_value=False)
    @patch("courses.views.instructor_views.CourseSectionFormSet")
    @patch("courses.views.instructor_views.CourseForm")
    def test_student_cannot_create_course_in_active_organization(
        self,
        course_form_class,
        formset_class,
        can_create_course_mock,
    ):
        from courses.views import instructor_views

        request = RequestFactory().post("/instructor/course/create/")
        request.user = self._user()
        request.organization = object()

        response = instructor_views.course_create(request)

        self.assertEqual(response.status_code, 403)
        can_create_course_mock.assert_called_once_with(
            request.user,
            request.organization,
        )
        course_form_class.assert_not_called()
        formset_class.assert_not_called()

    @patch("courses.views.instructor_views.can_create_course", return_value=False)
    def test_student_cannot_create_platform_course_without_organization(
        self,
        can_create_course_mock,
    ):
        from courses.views import instructor_views

        request = RequestFactory().post("/instructor/course/create/")
        request.user = self._user()

        response = instructor_views.course_create(request)

        self.assertEqual(response.status_code, 403)
        can_create_course_mock.assert_called_once_with(request.user, None)

    @patch("courses.services.permissions.get_active_membership")
    def test_student_role_cannot_create_course(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        get_active_membership.return_value = SimpleNamespace(
            role=OrganizationRole.STUDENT,
        )

        self.assertFalse(can_create_course(user, organization))
        get_active_membership.assert_called_once_with(user, organization)

    @patch("courses.services.permissions.get_active_membership")
    def test_staff_can_create_course_in_organization(
        self,
        get_active_membership,
    ):
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
