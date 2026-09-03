from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from quiz.models import Category, Domain, Exam


User = get_user_model()


class ExamCatalogPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="catalog-page-user",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.domain = Domain.objects.create(
            name="AWS",
            slug="aws",
            is_active=True,
        )
        self.category = Category.objects.create(
            name="AWS Core",
            slug="aws-core",
            domain=self.domain,
            is_active=True,
        )

    def test_courses_and_exams_have_domain_first_catalog_and_correct_links(self):
        course = Course.objects.create(
            title="AWS Cloud Practitioner Course",
            description="Course catalog test",
            category=self.category,
            level="beginner",
            is_public=True,
            is_published=True,
            approval_status=Course.APPROVAL_APPROVED,
        )
        exam = Exam.objects.create(
            title="AWS Final Assessment",
            primary_category=self.category,
            question_count=10,
            duration_seconds=1800,
            passing_score=70,
            is_published=True,
            is_free=False,
            price=Decimal("250.00"),
        )

        response = self.client.get(reverse("quiz:exam_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explore by domain")
        self.assertContains(response, "AWS")
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
        self.assertContains(response, "domain-card")
        self.assertContains(response, "resource-card")
