from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from quiz.models import Exam, UserExam


class LearningActivityClearHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="history-user",
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
        self.attempt = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            status=UserExam.STATUS_SUBMITTED,
            submitted_at="2026-09-05T10:00:00Z",
            question_order=[],
            score=80,
            passed=True,
        )

    def test_clear_learning_history_deletes_submitted_exam_history(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("quiz:clear_learning_history")
        )

        self.assertRedirects(response, reverse("quiz:student_dashboard"))
        self.assertFalse(UserExam.objects.filter(pk=self.attempt.pk).exists())

    def test_clear_learning_history_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("quiz:clear_learning_history")
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(UserExam.objects.filter(pk=self.attempt.pk).exists())
