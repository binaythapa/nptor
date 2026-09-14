from datetime import timedelta

from django.test import SimpleTestCase
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
