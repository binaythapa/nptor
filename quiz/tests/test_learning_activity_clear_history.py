from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from quiz.models import Exam, LearningActivityDismissal, UserExam


class LearningActivityRemoveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="history-user",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other-history-user",
            password="test-password",
        )
        self.exam = Exam.objects.create(
            title="History Test Exam",
            question_count=1,
            duration_seconds=600,
            level=1,
            passing_score=70,
            is_published=True,
        )
        self.other_exam = Exam.objects.create(
            title="Other History Test Exam",
            question_count=1,
            duration_seconds=600,
            level=1,
            passing_score=70,
            is_published=True,
        )
        self.attempt = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at=timezone.now(),
            question_order=[],
            score=80,
            passed=True,
        )
        self.other_attempt = UserExam.objects.create(
            user=self.other_user,
            exam=self.other_exam,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at=timezone.now(),
            question_order=[],
            score=60,
            passed=False,
        )

    def test_remove_exam_activity_hides_item_without_deleting_attempt(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "quiz:remove_learning_activity",
                args=["exam", self.exam.id],
            )
        )

        self.assertRedirects(response, reverse("quiz:student_dashboard"))
        self.assertTrue(UserExam.objects.filter(pk=self.attempt.pk).exists())
        self.assertTrue(
            LearningActivityDismissal.objects.filter(
                user=self.user,
                resource_type="exam",
                resource_id=self.exam.id,
            ).exists()
        )

    def test_removal_is_scoped_to_logged_in_user(self):
        self.client.force_login(self.user)

        self.client.post(
            reverse(
                "quiz:remove_learning_activity",
                args=["exam", self.other_exam.id],
            )
        )

        self.assertFalse(
            LearningActivityDismissal.objects.filter(
                user=self.other_user,
                resource_type="exam",
                resource_id=self.other_exam.id,
            ).exists()
        )
        self.assertTrue(UserExam.objects.filter(pk=self.other_attempt.pk).exists())

    def test_remove_learning_activity_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "quiz:remove_learning_activity",
                args=["exam", self.exam.id],
            )
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(
            LearningActivityDismissal.objects.filter(
                user=self.user,
                resource_type="exam",
                resource_id=self.exam.id,
            ).exists()
        )

    def test_removed_item_is_not_rendered_in_dashboard(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse(
                "quiz:remove_learning_activity",
                args=["exam", self.exam.id],
            )
        )

        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertNotContains(response, self.exam.title)
