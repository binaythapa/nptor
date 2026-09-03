from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Question


class QuestionMutationAuthorizationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username="question-staff",
            password="test-password",
            is_staff=True,
        )
        self.admin_user = User.objects.create_superuser(
            username="question-admin",
            password="test-password",
            email="question-admin@example.com",
        )
        self.question = Question.objects.create(
            text="Original question",
            difficulty=Question.EASY,
            question_type=Question.SINGLE,
            is_active=True,
            created_by=self.admin_user,
        )

    def test_staff_cannot_add_question(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse("quiz:add_question"),
            {
                "text": "Unauthorized question",
                "difficulty": Question.EASY,
                "question_type": Question.SINGLE,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            Question.objects.filter(text="Unauthorized question").exists()
        )

    def test_staff_cannot_edit_question_or_correct_answer(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse("quiz:edit_question", kwargs={"pk": self.question.pk}),
            {
                "text": "Tampered question",
                "difficulty": Question.HARD,
                "question_type": Question.SINGLE,
                "choices-TOTAL_FORMS": "0",
                "choices-INITIAL_FORMS": "0",
                "choices-MIN_NUM_FORMS": "0",
                "choices-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.question.refresh_from_db()
        self.assertEqual(self.question.text, "Original question")
        self.assertEqual(self.question.difficulty, Question.EASY)

    def test_staff_cannot_toggle_question_active(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse("quiz:toggle_question_active"),
            {"id": self.question.pk},
        )

        self.assertEqual(response.status_code, 403)
        self.question.refresh_from_db()
        self.assertTrue(self.question.is_active)

    def test_staff_cannot_delete_question(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse("quiz:delete_question", kwargs={"pk": self.question.pk}),
        )

        self.assertEqual(response.status_code, 403)
        self.question.refresh_from_db()
        self.assertFalse(self.question.is_deleted)

    def test_superuser_can_edit_question(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("quiz:edit_question", kwargs={"pk": self.question.pk}),
            {
                "text": "Admin updated question",
                "difficulty": Question.HARD,
                "question_type": Question.SINGLE,
                "choices-TOTAL_FORMS": "0",
                "choices-INITIAL_FORMS": "0",
                "choices-MIN_NUM_FORMS": "0",
                "choices-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertNotEqual(response.status_code, 403)
        self.question.refresh_from_db()
        self.assertEqual(self.question.text, "Admin updated question")
