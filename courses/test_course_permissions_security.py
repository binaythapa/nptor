from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from courses.models.section import CourseSection
from courses.services.permissions import can_edit_course
from organizations.models.role import OrganizationRole


class CourseEditAuthorizationTests(TestCase):
    def _user(self, *, superuser=False):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=superuser,
        )

    def _course(self, *, organization=None, created_by=None):
        return SimpleNamespace(
            organization=organization,
            created_by=created_by,
        )

    def test_superuser_can_edit_any_course(self):
        user = self._user(superuser=True)
        course = self._course(organization=object())

        self.assertTrue(can_edit_course(user, course))

    def test_creator_can_edit_platform_course(self):
        user = self._user()
        course = self._course(created_by=user)

        self.assertTrue(can_edit_course(user, course))

    @patch("courses.services.permissions.get_active_membership")
    def test_creator_cannot_edit_org_course_without_active_membership(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        course = self._course(
            organization=organization,
            created_by=user,
        )
        get_active_membership.return_value = None

        self.assertFalse(can_edit_course(user, course))
        get_active_membership.assert_called_once_with(user, organization)

    @patch("courses.services.permissions.get_active_membership")
    def test_org_course_creator_requires_teaching_role(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        course = self._course(
            organization=organization,
            created_by=user,
        )

        get_active_membership.return_value = SimpleNamespace(
            role=OrganizationRole.STUDENT,
        )

        self.assertFalse(can_edit_course(user, course))

    @patch("courses.services.permissions.get_active_membership")
    def test_org_course_creator_with_active_teaching_role_can_edit(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        course = self._course(
            organization=organization,
            created_by=user,
        )

        get_active_membership.return_value = SimpleNamespace(
            role=OrganizationRole.STAFF,
        )

        self.assertTrue(can_edit_course(user, course))


class CourseSectionAuthorizationTests(TestCase):
    @patch("courses.services.permissions.can_edit_course")
    def test_section_delete_permission_delegates_to_course_authorization(
        self,
        can_edit_course_mock,
    ):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        course = SimpleNamespace(created_by=object(), organization=object())
        section = CourseSection(course=course, title="Section", order=1)
        can_edit_course_mock.return_value = True

        self.assertTrue(section.can_be_deleted_by(user))
        can_edit_course_mock.assert_called_once_with(user, course)

    @patch("courses.services.permissions.can_edit_course")
    def test_section_delete_permission_denies_when_course_edit_is_denied(
        self,
        can_edit_course_mock,
    ):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        course = SimpleNamespace(created_by=user, organization=object())
        section = CourseSection(course=course, title="Section", order=1)
        can_edit_course_mock.return_value = False

        self.assertFalse(section.can_be_deleted_by(user))
        can_edit_course_mock.assert_called_once_with(user, course)
