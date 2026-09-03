from django.test import TestCase
from django.urls import reverse

from quiz.models import Choice, Domain, Category, Question


class PracticeProgressTests(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(
            name="[TEST] Progress Domain",
            slug="test-progress-domain",
            is_active=True,
        )
        self.category = Category.objects.create(
            domain=self.domain,
            name="Compute",
            slug="test-progress-compute",
            is_active=True,
        )
        self.question = Question.objects.create(
            primary_category=self.category,
            question_type=Question.SINGLE,
            difficulty=Question.EASY,
            text="Progress question",
            is_active=True,
            is_deleted=False,
        )
        self.choice = Choice.objects.create(
            question=self.question,
            text="Correct",
            is_correct=True,
        )

    def _start_practice(self):
        response = self.client.get(
            reverse("quiz:practice"),
            {"domain": self.domain.id},
        )
        self.assertEqual(response.status_code, 200)
        return self.client.session

    def test_answer_ajax_marks_question_seen_and_returns_progress(self):
        session = self._start_practice()
        self.assertEqual(session["p_qid"], self.question.id)
        self.assertEqual(session["p_seen"], [])

        response = self.client.post(
            reverse("quiz:practice_answer_ajax"),
            {
                "question_id": self.question.id,
                "choice": self.choice.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["progress_done"], 1)
        self.assertEqual(data["progress_total"], 1)

        session = self.client.session
        self.assertEqual(session["p_seen"], [self.question.id])
        self.assertNotIn("p_qid", session)

    def test_next_after_answer_does_not_double_count_question(self):
        self._start_practice()

        self.client.post(
            reverse("quiz:practice_answer_ajax"),
            {
                "question_id": self.question.id,
                "choice": self.choice.id,
            },
        )

        response = self.client.post(
            reverse("quiz:practice_next_ajax"),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["progress_done"], 1)
        self.assertEqual(data["progress_total"], 1)
