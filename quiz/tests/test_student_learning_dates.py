from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from quiz.views.student_learning_dashboard import _assignment_timeline


class StudentLearningAssignmentTimelineTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def assignment(self, **overrides):
        class Assignment:
            starts_at = None
            due_at = None
            expires_at = None

        assignment = Assignment()
        for key, value in overrides.items():
            setattr(assignment, key, value)
        return assignment

    def test_future_start_is_not_available_yet(self):
        assignment = self.assignment(starts_at=self.now + timedelta(days=2))
        result = _assignment_timeline(assignment, self.now)
        self.assertEqual(result["state"], "not_started")
        self.assertEqual(result["label"], "Available soon")

    @override_settings(TIME_ZONE="Asia/Kathmandu")
    def test_future_timestamp_on_same_local_calendar_date_is_available(self):
        now = datetime(2026, 9, 14, 20, 0, tzinfo=dt_timezone.utc)
        starts_at = datetime(2026, 9, 14, 23, 0, tzinfo=dt_timezone.utc)
        result = _assignment_timeline(self.assignment(starts_at=starts_at), now)
        self.assertEqual(timezone.localtime(now).date(), timezone.localtime(starts_at).date())
        self.assertEqual(result["state"], "active")
        self.assertTrue(result["can_access"])

    def test_due_date_marks_assignment_overdue_without_expiring_access(self):
        assignment = self.assignment(
            starts_at=self.now - timedelta(days=5),
            due_at=self.now - timedelta(days=1),
            expires_at=self.now + timedelta(days=5),
        )
        result = _assignment_timeline(assignment, self.now)
        self.assertEqual(result["state"], "overdue")
        self.assertEqual(result["label"], "Overdue")
        self.assertTrue(result["can_access"])

    def test_expiration_blocks_access(self):
        assignment = self.assignment(
            starts_at=self.now - timedelta(days=5),
            due_at=self.now - timedelta(days=1),
            expires_at=self.now - timedelta(hours=1),
        )
        result = _assignment_timeline(assignment, self.now)
        self.assertEqual(result["state"], "expired")
        self.assertEqual(result["label"], "Access expired")
        self.assertFalse(result["can_access"])
