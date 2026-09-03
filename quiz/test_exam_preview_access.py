from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, Choice, Domain, Exam, Question, UserExam


User = get_user_model()


class ExamPreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="exam-preview-user",
            password="test-password",
        )
        self.domain = Domain.objects.create(
            name="AWS",
            slug="aws",
            is_active=True,
        )
        self.category = Category.objects.create(
            name="Cloud Practitioner",
            slug="cloud-practitioner",
            domain=self.domain,
            is_active=True,
        )
        self.exam = Exam.objects.create(
            title="AWS Practice Exam",
            primary_category=self.category,
            question_count=20,
            duration_seconds=3600,
            passing_score=70,
            is_published=True,
            is_free=False,
        )
        for index in range(5):
            question = Question.objects.create(
                text=f"Question {index + 1}",
                question_type=Question.SINGLE,
                difficulty=Question.MEDIUM,
                primary_category=self.category,
                is_active=True,
                is_deleted=False,
            )
            Choice.objects.create(
                question=question,
                text="Option A",
                order=1,
            )
            Choice.objects.create(
                question=question,
                text="Option B",
                order=2,
            )

    def test_paid_exam_preview_requires_login(self):
        response = self.client.get(
            reverse("quiz:exam_preview", args=[self.exam.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_preview_shows_bounded_sample_without_creating_attempt(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("quiz:exam_preview", args=[self.exam.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["questions"]), 3)
        self.assertFalse(UserExam.objects.filter(user=self.user).exists())
        self.assertContains(response, "Get full access")

    def test_free_exam_preview_redirects_to_real_start(self):
        self.exam.is_free = True
        self.exam.save(update_fields=["is_free"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("quiz:exam_preview", args=[self.exam.id])
        )

        self.assertRedirects(
            response,
            reverse("quiz:exam_start", args=[self.exam.id]),
        )
