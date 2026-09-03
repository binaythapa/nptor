from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from quiz.models import Choice, Exam, Question, UserAnswer, UserExam


User = get_user_model()


class ExamAttemptExpiryTests(TestCase):
    def test_expired_post_saves_current_answer_before_submission(self):
        user = User.objects.create_user(
            username="expiry-test-user",
            password="test-password",
        )
        exam = Exam.objects.create(
            title="Expiry Test Exam",
            question_count=1,
            duration_seconds=60,
            passing_score=50,
            is_free=True,
            is_published=True,
        )
        question = Question.objects.create(
            text="Which option is correct?",
            question_type=Question.SINGLE,
            difficulty=Question.EASY,
        )
        correct = Choice.objects.create(
            question=question,
            text="Correct",
            is_correct=True,
        )
        ue = UserExam.objects.create(
            user=user,
            exam=exam,
            question_order=[question.id],
            current_index=0,
        )
        UserAnswer.objects.create(
            user_exam=ue,
            question=question,
        )
        UserExam.objects.filter(pk=ue.pk).update(
            started_at=timezone.now() - timedelta(seconds=120),
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse(
                "quiz:exam_question",
                args=[ue.id, 0],
            ),
            {
                f"question_{question.id}": str(correct.id),
                "nav": "review",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            response.url,
            reverse(
                "quiz:exam_submit",
                args=[ue.id],
            ),
        )

        answer = UserAnswer.objects.get(
            user_exam=ue,
            question=question,
        )
        self.assertEqual(
            answer.choice_id,
            correct.id,
        )
