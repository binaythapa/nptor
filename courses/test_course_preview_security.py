from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from courses.services.permissions import can_preview_course


class CoursePreviewAuthorizationTests(TestCase):
    def _user(self, *, superuser=False, staff=False):
        return SimpleNamespace(
            id=1,
            is_authenticated=True,
            is_superuser=superuser,
            is_staff=staff,
        )

    def _course(self, *, organization=None, created_by=None):
        return SimpleNamespace(
            organization=organization,
            created_by=created_by,
        )

    def test_superuser_can_preview_any_course(self):
        user = self._user(superuser=True)
        course = self._course(organization=object())

        self.assertTrue(can_preview_course(user, course))

    def test_staff_can_preview_any_course(self):
        user = self._user(staff=True)
        course = self._course(organization=object())

        self.assertTrue(can_preview_course(user, course))

    def test_platform_creator_can_preview_own_course(self):
        user = self._user()
        course = self._course(created_by=user)

        self.assertTrue(can_preview_course(user, course))

    @patch("courses.services.permissions.get_active_membership")
    def test_org_creator_cannot_preview_after_membership_is_removed(
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

        self.assertFalse(can_preview_course(user, course))
        get_active_membership.assert_called_once_with(user, organization)

    @patch("courses.services.permissions.get_active_membership")
    def test_org_creator_needs_teaching_role_to_preview(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        course = self._course(
            organization=organization,
            created_by=user,
        )
        get_active_membership.return_value = SimpleNamespace(role="student")

        self.assertFalse(can_preview_course(user, course))

    @patch("courses.services.permissions.get_active_membership")
    def test_org_creator_with_teaching_role_can_preview(
        self,
        get_active_membership,
    ):
        user = self._user()
        organization = object()
        course = self._course(
            organization=organization,
            created_by=user,
        )
        get_active_membership.return_value = SimpleNamespace(role="staff")

        with patch(
            "courses.services.permissions.OrganizationRole.teaching_roles",
            return_value={"staff"},
        ):
            self.assertTrue(can_preview_course(user, course))
