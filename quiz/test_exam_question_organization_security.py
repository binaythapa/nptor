from django.contrib.auth import get_user_model
from django.test import TestCase

from organizations.models.organization import Organization
from quiz.forms import QuestionForm
from quiz.models import Category, Domain


User = get_user_model()


class ExamQuestionOrganizationBoundaryTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(
            name="Exam Security A",
            slug="exam-security-a",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.org_b = Organization.objects.create(
            name="Exam Security B",
            slug="exam-security-b",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.domain_a = Domain.objects.create(
            name="Domain A",
            slug="domain-a",
            organization=self.org_a,
        )
        self.domain_b = Domain.objects.create(
            name="Domain B",
            slug="domain-b",
            organization=self.org_b,
        )
        self.category_a = Category.objects.create(
            name="Category A",
            slug="category-a",
            domain=self.domain_a,
            organization=self.org_a,
        )
        self.category_b = Category.objects.create(
            name="Category B",
            slug="category-b",
            domain=self.domain_b,
            organization=self.org_b,
        )

    def _data(self, category):
        return {
            "primary_category": str(category.id),
            "categories": [str(category.id)],
            "difficulty": "medium",
            "question_type": "single",
            "text": "Organization boundary question",
            "explanation": "Explanation",
        }

    def test_question_form_rejects_cross_organization_category_on_create(self):
        form = QuestionForm(
            data=self._data(self.category_b),
            organization=self.org_a,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("primary_category", form.errors)
        self.assertIn("categories", form.errors)

    def test_question_form_allows_same_organization_category(self):
        form = QuestionForm(
            data=self._data(self.category_a),
            organization=self.org_a,
        )

        self.assertTrue(form.is_valid(), form.errors)
