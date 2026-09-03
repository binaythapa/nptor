from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Choice, Exam, Question, UserAnswer, UserExam


User = get_user_model()


class ExamAttemptExpiryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expiry-test-user",
            password="test-password",
        )
        self.exam = Exam.objects.create(
            title="Expiry Test Exam",
            question_count=1,
            duration_seconds=60,
            passing_score=50,
            is_free=True,
            is_published=True,
        )
        self.question = Question.objects.create(
            text="Which option is correct?",
            question_type=Question.SINGLE,
            difficulty=Question.EASY,
        )
        self.correct = Choice.objects.create(
            question=self.question,
            text="Correct",
            is_correct=True,
        )
        self.ue = UserExam.objects.create(
            user=self.user,
            exam=self.exam,
            question_order=[self.question.id],
            current_index=0,
        )
        UserAnswer.objects.create(
            user_exam=self.ue,
            question=self.question,
        )
        self.client.force_login(self.user)

    def test_timer_expiry_submits_directly_to_exam_submit_endpoint(self):
        response = self.client.get(
            reverse(
                "quiz:exam_question",
                args=[self.ue.id, 0],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse(
                "quiz:exam_submit",
                args=[self.ue.id],
            )
        )
        self.assertContains(response, "form.action =")
