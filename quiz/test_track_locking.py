from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from quiz.models import Exam, ExamTrack, UserExam
from quiz.services.access import can_access_exam
from quiz.services.track_progress import build_track_progress


class TrackLockingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="track-student",
            password="password",
        )
        self.track = ExamTrack.objects.create(
            title="Certification Track",
            slug="certification-track",
            pricing_type=ExamTrack.PRICING_FREE,
            is_active=True,
        )
        self.first = Exam.objects.create(
            title="Foundation Exam",
            track=self.track,
            duration_seconds=3600,
            question_count=20,
            passing_score=70,
            is_free=True,
            is_published=True,
        )
        self.second = Exam.objects.create(
            title="Advanced Exam",
            track=self.track,
            duration_seconds=3600,
            question_count=30,
            passing_score=80,
            is_free=True,
            is_published=True,
        )

    def test_first_exam_is_unlocked_and_next_exam_requires_a_passed_previous_exam(self):
        progress = build_track_progress(self.user, self.track)

        self.assertEqual(
            [item["exam"] for item in progress["items"]],
            [self.first, self.second],
        )
        self.assertTrue(progress["items"][0]["is_unlocked"])
        self.assertFalse(progress["items"][1]["is_unlocked"])
        self.assertEqual(
            progress["items"][1]["lock_reason"],
            "Complete the previous exam with a passing score.",
        )

        allowed, reason = can_access_exam(self.user, self.second)

        self.assertFalse(allowed)
        self.assertEqual(reason, "Previous track exam required")

    def test_passing_previous_exam_unlocks_next_exam(self):
        UserExam.objects.create(
            user=self.user,
            exam=self.first,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at=timezone.now(),
            score=70,
            passed=True,
        )

        progress = build_track_progress(self.user, self.track)

        self.assertTrue(progress["items"][1]["is_unlocked"])
        self.assertIsNone(progress["items"][1]["lock_reason"])

        allowed, reason = can_access_exam(self.user, self.second)

        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_failing_previous_exam_keeps_next_exam_locked(self):
        UserExam.objects.create(
            user=self.user,
            exam=self.first,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at=timezone.now(),
            score=69,
            passed=False,
        )

        progress = build_track_progress(self.user, self.track)

        self.assertFalse(progress["items"][1]["is_unlocked"])
        self.assertEqual(
            progress["items"][1]["lock_reason"],
            "Pass the previous exam to unlock this exam.",
        )

        allowed, reason = can_access_exam(self.user, self.second)

        self.assertFalse(allowed)
        self.assertEqual(reason, "Previous track exam required")

    def test_track_progress_counts_only_passed_exams(self):
        UserExam.objects.create(
            user=self.user,
            exam=self.first,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at=timezone.now(),
            score=75,
            passed=True,
        )

        progress = build_track_progress(self.user, self.track)

        self.assertEqual(progress["completed_count"], 1)
        self.assertEqual(progress["total_count"], 2)
        self.assertEqual(progress["percent"], 50)
