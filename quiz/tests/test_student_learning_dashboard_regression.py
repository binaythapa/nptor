from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from quiz.models import Category, Domain, Exam
from quiz.services.learning_catalog import build_learning_catalog


class StudentLearningDashboardRegressionTests(TestCase):
    def test_dashboard_does_not_reference_removed_exam_primary_category(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="learning-dashboard-user",
            password="pass",
        )
        self.client.login(username="learning-dashboard-user", password="pass")

        response = self.client.get(reverse("quiz:student_dashboard"))

        self.assertEqual(response.status_code, 200)

    def test_learning_catalog_uses_exam_categories_instead_of_primary_category(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="catalog-category-user",
            password="pass",
        )
        domain = Domain.objects.create(name="SQL", slug="sql", is_active=True)
        category = Category.objects.create(
            name="SQL Fundamentals",
            slug="sql-fundamentals",
            domain=domain,
            is_active=True,
        )
        exam = Exam.objects.create(
            title="SQL Basics",
            duration_seconds=600,
            is_published=True,
            organization=None,
            question_count=5,
        )
        exam.categories.add(category)

        catalog = build_learning_catalog(user=user, resource_type="all")

        self.assertTrue(any(item["resource"].id == exam.id for item in catalog["resources"]))
