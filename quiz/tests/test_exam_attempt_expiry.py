from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
            reverse("quiz:exam_question", args=[self.ue.id, 0])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("quiz:exam_submit", args=[self.ue.id]),
        )
        self.assertContains(response, "form.action =")

    def test_expired_submission_grades_posted_answer(self):
        UserExam.objects.filter(pk=self.ue.pk).update(
            started_at=timezone.now() - timedelta(seconds=120),
        )

        response = self.client.post(
            reverse("quiz:exam_submit", args=[self.ue.id]),
            {f"question_{self.question.id}": str(self.correct.id)},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("quiz:exam_result", args=[self.ue.id]),
        )

        self.ue.refresh_from_db()
        answer = UserAnswer.objects.get(
            user_exam=self.ue,
            question=self.question,
        )

        self.assertEqual(answer.choice_id, self.correct.id)
        self.assertTrue(answer.is_correct)
        self.assertEqual(self.ue.score, 100.0)
        self.assertTrue(self.ue.passed)
        self.assertEqual(self.ue.status, UserExam.STATUS_SUBMITTED)
        self.assertIsNotNone(self.ue.submitted_at)

    def test_expired_page_finalizes_saved_answer_without_clearing_it(self):
        UserAnswer.objects.filter(pk=self.ue.answers.get().pk).update(
            choice=self.correct,
        )
        UserExam.objects.filter(pk=self.ue.pk).update(
            started_at=timezone.now() - timedelta(seconds=120),
        )

        response = self.client.get(
            reverse("quiz:exam_question", args=[self.ue.id, 0])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("quiz:student_dashboard"),
        )

        self.ue.refresh_from_db()
        answer = self.ue.answers.get()
        self.assertEqual(answer.choice_id, self.correct.id)
        self.assertTrue(answer.is_correct)
        self.assertEqual(self.ue.score, 100.0)
        self.assertTrue(self.ue.passed)
        self.assertEqual(self.ue.status, UserExam.STATUS_SUBMITTED)
        self.assertIsNotNone(self.ue.submitted_at)

    def test_exam_submit_direct_get_does_not_submit_attempt(self):
        response = self.client.get(
            reverse("quiz:exam_submit", args=[self.ue.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("quiz:student_dashboard"),
        )
        self.ue.refresh_from_db()
        self.assertIsNone(self.ue.submitted_at)
        self.assertIsNone(self.ue.score)
