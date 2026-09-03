from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from quiz.models import Exam, UserExam
from quiz.views.exams import exam_submit

User = get_user_model()


class ExamSubmissionAuthorizationTests(TestCase):
    def test_exam_submit_rejects_get_requests(self):
        user = User.objects.create_user(
            username="submit-security-user",
            email="submit-security@example.com",
            password="password",
        )
        exam = Exam.objects.create(
            title="Submission Security Exam",
            duration_seconds=60,
        )
        attempt = UserExam.objects.create(user=user, exam=exam)
        request = RequestFactory().get("/")
        request.user = user
        response = exam_submit(request, attempt.id)
        self.assertEqual(response.status_code, 405)
