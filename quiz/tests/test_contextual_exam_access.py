from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, Domain, Exam


class ContextualExamAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="context-exam-user",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        self.domain = Domain.objects.create(name="Context Domain", slug="context-domain")
        self.category = Category.objects.create(
            name="Context Category",
            slug="context-category",
            domain=self.domain,
        )
        self.exam = Exam.objects.create(
            title="Contextual Exam",
            primary_category=self.category,
            question_count=1,
            duration_seconds=600,
            level=1,
            passing_score=50,
            is_published=True,
        )

    def test_direct_exam_detail_redirects_to_catalog(self):
        response = self.client.get(reverse("quiz:exam_detail", args=[self.exam.id]))
        self.assertRedirects(response, reverse("quiz:exam_list"), fetch_redirect_response=False)

    def test_direct_exam_start_redirects_to_catalog(self):
        response = self.client.get(reverse("quiz:exam_start", args=[self.exam.id]))
        self.assertRedirects(response, reverse("quiz:exam_list"), fetch_redirect_response=False)

    def test_track_page_passes_track_context_when_starting_exam(self):
        root = Path(__file__).resolve().parents[2]
        template = (
            root / "templates" / "quiz" / "student" / "learning_track.html"
        ).read_text(encoding="utf-8")
        self.assertIn("?track={{ track.slug }}", template)


if __name__ == "__main__":
    import unittest

    unittest.main()
