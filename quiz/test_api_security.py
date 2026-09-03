from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from quiz.api_urls import start_exam_authorized
from quiz.api_views import attempt_detail, api_submit_attempt
from quiz.models import Exam, UserExam


class ExamAPIAuthorizationRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api-security-user",
            email="api-security-user@example.com",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="api-security-other-user",
            email="api-security-other-user@example.com",
            password="test-password",
        )
        self.exam = Exam.objects.create(
            title="Paid API Security Exam",
            duration_seconds=3600,
            question_count=1,
            is_free=False,
            price=100,
            is_published=True,
        )
        self.factory = APIRequestFactory()

    @patch("quiz.api_urls.api_views.allocate_questions_for_exam")
    def test_paid_exam_api_start_requires_access(self, allocate):
        request = self.factory.post(
            f"/api/exams/{self.exam.id}/start/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = start_exam_authorized(request, self.exam.id)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(UserExam.objects.filter(user=self.user).count(), 0)
        allocate.assert_not_called()

    def test_attempt_detail_is_scoped_to_attempt_owner(self):
        attempt = UserExam.objects.create(
            user=self.other_user,
            exam=self.exam,
        )

        request = self.factory.get(
            f"/api/attempts/{attempt.id}/",
        )
        force_authenticate(request, user=self.user)

        response = attempt_detail(request, attempt.id)

        self.assertEqual(response.status_code, 404)

    def test_attempt_submit_is_scoped_to_attempt_owner(self):
        attempt = UserExam.objects.create(
            user=self.other_user,
            exam=self.exam,
        )

        request = self.factory.post(
            f"/api/attempts/{attempt.id}/submit/",
            {"answers": {}},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = api_submit_attempt(request, attempt.id)

        self.assertEqual(response.status_code, 404)
        attempt.refresh_from_db()
        self.assertIsNone(attempt.submitted_at)
