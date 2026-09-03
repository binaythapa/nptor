from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import Exam


User = get_user_model()


class ExamCatalogPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="catalog-page-user",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_courses_and_exams_have_separate_compact_sections_and_correct_links(self):
        course = Course.objects.create(
            title="AWS Cloud Practitioner Course",
            description="Course catalog test",
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        exam = Exam.objects.create(
            title="AWS Final Assessment",
            question_count=10,
            duration_seconds=1800,
            passing_score=70,
            is_published=True,
            is_free=False,
            price=Decimal("250.00"),
        )

        response = self.client.get(reverse("quiz:exam_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Courses")
        self.assertContains(response, "Exams")
        self.assertContains(response, course.title)
        self.assertContains(response, exam.title)
        self.assertContains(
            response,
            reverse("courses:subscribe_course", kwargs={"course_id": course.id}),
        )
        self.assertContains(
            response,
            reverse("payments:exam_checkout", kwargs={"exam_id": exam.id}),
        )
        self.assertContains(response, "catalog-card")
        self.assertContains(response, "catalog-page")
