from types import SimpleNamespace
from unittest import TestCase

from courses.services.permissions import can_modify_course_content


class CourseMutationAuthorizationTests(TestCase):
    def _user(self, *, superuser=False):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=superuser,
        )

    def _course(self, status):
        return SimpleNamespace(
            approval_status=status,
            organization=None,
            created_by=None,
        )

    def test_superuser_can_modify_any_course_state(self):
        user = self._user(superuser=True)
        for status in ("draft", "pending", "approved", "changes_required", "rejected"):
            self.assertTrue(can_modify_course_content(user, self._course(status)))

    def test_platform_creator_can_modify_draft(self):
        user = self._user()
        course = self._course("draft")
        course.created_by = user

        self.assertTrue(can_modify_course_content(user, course))

    def test_platform_creator_can_modify_changes_required(self):
        user = self._user()
        course = self._course("changes_required")
        course.created_by = user

        self.assertTrue(can_modify_course_content(user, course))

    def test_platform_creator_can_modify_rejected(self):
        user = self._user()
        course = self._course("rejected")
        course.created_by = user

        self.assertTrue(can_modify_course_content(user, course))

    def test_platform_creator_cannot_modify_pending(self):
        user = self._user()
        course = self._course("pending")
        course.created_by = user

        self.assertFalse(can_modify_course_content(user, course))

    def test_platform_creator_cannot_modify_approved(self):
        user = self._user()
        course = self._course("approved")
        course.created_by = user

        self.assertFalse(can_modify_course_content(user, course))
