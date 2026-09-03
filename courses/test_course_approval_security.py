from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from courses.services.course_approval import (
    approve_course,
    publish_course,
    reject_course,
    request_course_changes,
    submit_course_for_review,
)
from courses.services.permissions import (
    can_approve_course,
    can_publish_course,
    can_request_changes,
    can_reject_course,
    can_submit_course_for_review,
)


class CourseApprovalAuthorizationTests(TestCase):
    def _user(self, *, superuser=False):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=superuser,
        )

    def _course(self, *, status="draft", approved=False):
        return SimpleNamespace(
            approval_status=status,
            is_published=False,
            created_by=None,
            organization=None,
            is_approved=lambda: approved,
        )

    @patch("courses.services.permissions.can_edit_course", return_value=False)
    def test_student_or_unauthorized_user_cannot_submit_course(self, can_edit_mock):
        user = self._user()
        course = self._course()

        self.assertFalse(can_submit_course_for_review(user, course))
        can_edit_mock.assert_called_once_with(user, course)

    @patch("courses.services.permissions.can_edit_course", return_value=True)
    def test_submit_allows_only_supported_states(self, can_edit_mock):
        user = self._user()

        for status in ("draft", "changes_required", "rejected"):
            course = self._course(status=status)
            self.assertTrue(can_submit_course_for_review(user, course))

        pending = self._course(status="pending")
        approved = self._course(status="approved")
        self.assertFalse(can_submit_course_for_review(user, pending))
        self.assertFalse(can_submit_course_for_review(user, approved))

    def test_only_superuser_can_moderate(self):
        regular_user = self._user()
        admin = self._user(superuser=True)
        pending = self._course(status="pending")

        self.assertFalse(can_approve_course(regular_user, pending))
        self.assertFalse(can_request_changes(regular_user, pending))
        self.assertFalse(can_reject_course(regular_user, pending))
        self.assertTrue(can_approve_course(admin, pending))
        self.assertTrue(can_request_changes(admin, pending))
        self.assertTrue(can_reject_course(admin, pending))

    def test_only_superuser_can_publish_approved_course(self):
        regular_user = self._user()
        admin = self._user(superuser=True)
        approved = self._course(status="approved", approved=True)

        self.assertFalse(can_publish_course(regular_user, approved))
        self.assertTrue(can_publish_course(admin, approved))

    @patch("courses.services.course_approval.can_edit_course", return_value=False)
    def test_publish_service_rejects_non_editor(self, can_edit_mock):
        user = self._user()
        course = self._course(status="approved", approved=True)

        with self.assertRaises(PermissionError):
            publish_course(course=course, user=user)

        can_edit_mock.assert_called_once_with(user, course)

    @patch("courses.services.course_approval.can_submit_course_for_review", return_value=False)
    def test_submit_service_rejects_unauthorized_user(self, permission_mock):
        user = self._user()
        course = self._course()

        with self.assertRaises(PermissionError):
            submit_course_for_review(course=course, user=user)

        permission_mock.assert_called_once_with(user, course)

    @patch("courses.services.course_approval.can_approve_course", return_value=False)
    def test_approve_service_rejects_unauthorized_user(self, permission_mock):
        user = self._user()
        course = self._course(status="pending")

        with self.assertRaises(PermissionError):
            approve_course(course=course, admin_user=user)

        permission_mock.assert_called_once_with(user, course)

    @patch("courses.services.course_approval.can_request_changes", return_value=False)
    def test_request_changes_service_rejects_unauthorized_user(self, permission_mock):
        user = self._user()
        course = self._course(status="pending")

        with self.assertRaises(PermissionError):
            request_course_changes(course=course, admin_user=user, notes="Fix it")

        permission_mock.assert_called_once_with(user, course)

    @patch("courses.services.course_approval.can_reject_course", return_value=False)
    def test_reject_service_rejects_unauthorized_user(self, permission_mock):
        user = self._user()
        course = self._course(status="pending")

        with self.assertRaises(PermissionError):
            reject_course(course=course, admin_user=user, notes="Not acceptable")

        permission_mock.assert_called_once_with(user, course)
