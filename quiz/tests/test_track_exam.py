from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from quiz.models import Exam, ExamTrack, TrackExam, UserExam
from quiz.services.track_progress import build_track_progress
from subscriptions.models import SubscriptionPlan


class TrackExamRelationshipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="track-test-user",
            password="test-password",
        )

        self.exam_a = self._exam("Exam A")
        self.exam_b = self._exam("Reusable Exam B")
        self.exam_c = self._exam("Exam C")

        self.track_one = ExamTrack.objects.create(
            title="Track One",
            slug="track-one",
        )
        self.track_two = ExamTrack.objects.create(
            title="Track Two",
            slug="track-two",
        )

        TrackExam.objects.create(
            track=self.track_one,
            exam=self.exam_a,
            order=1,
        )
        track_one_b = TrackExam.objects.create(
            track=self.track_one,
            exam=self.exam_b,
            order=2,
        )
        track_one_b.prerequisite_exams.add(self.exam_c)

        TrackExam.objects.create(
            track=self.track_two,
            exam=self.exam_a,
            order=1,
        )
        TrackExam.objects.create(
            track=self.track_two,
            exam=self.exam_b,
            order=2,
        )

        UserExam.objects.create(
            user=self.user,
            exam=self.exam_a,
            question_order=[],
            submitted_at=timezone.now(),
            passed=True,
            score=100,
        )

    @staticmethod
    def _exam(title):
        return Exam.objects.create(
            title=title,
            question_count=10,
            duration_seconds=600,
            passing_score=70,
            is_published=True,
        )

    def test_same_exam_can_belong_to_multiple_tracks(self):
        self.assertEqual(
            self.exam_b.track_memberships.count(),
            2,
        )

    def test_prerequisites_are_track_specific(self):
        first_progress = build_track_progress(self.user, self.track_one)
        first_item = first_progress["items"][1]
        self.assertFalse(first_item["is_unlocked"])
        self.assertEqual(
            first_item["lock_reason"],
            "Complete the prerequisite exam(s) first.",
        )

        second_progress = build_track_progress(self.user, self.track_two)
        second_item = second_progress["items"][1]
        self.assertTrue(second_item["is_unlocked"])

    def test_exam_pricing_is_externalized_to_subscription_plan(self):
        self.assertTrue(self.exam_b.is_free)

        plan = SubscriptionPlan.objects.create(
            name="Reusable Exam Direct Access",
            code="test-reusable-exam-direct",
            price=49,
            currency="INR",
            is_active=True,
        )
        self.exam_b.subscription_plans.add(plan)

        self.assertFalse(self.exam_b.is_free)
