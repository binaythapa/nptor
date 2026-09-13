from django.test import TestCase

from organizations.models import Organization
from quiz.forms import ExamForm
from quiz.models import Category


class OrganizationExamFormTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test School",
            slug="test-school",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.other_organization = Organization.objects.create(
            name="Other School",
            slug="other-school",
            org_type=Organization.TYPE_SCHOOL,
        )
        self.org_category = Category.objects.create(
            organization=self.organization,
            name="Mathematics",
            slug="mathematics",
        )
        self.other_category = Category.objects.create(
            organization=self.other_organization,
            name="Science",
            slug="science",
        )
        self.global_category = Category.objects.create(
            organization=None,
            name="Global",
            slug="global",
        )

    def test_organization_exam_form_shows_only_current_organization_categories(self):
        form = ExamForm(
            organization=self.organization,
            organization_categories_only=True,
        )

        primary_ids = set(form.fields["primary_category"].queryset.values_list("id", flat=True))
        category_ids = set(form.fields["categories"].queryset.values_list("id", flat=True))

        self.assertEqual(primary_ids, {self.org_category.pk})
        self.assertEqual(category_ids, {self.org_category.pk})
        self.assertEqual(form.fields["organization"].queryset.count(), 1)
        self.assertEqual(form.fields["organization"].queryset.first(), self.organization)

    def test_organization_exam_form_rejects_other_organization_category(self):
        form = ExamForm(
            {"title": "School Exam", "organization": self.organization.pk,
             "primary_category": self.other_category.pk,
             "categories": [self.other_category.pk], "question_count": 10,
             "duration_seconds": 600, "level": 1, "passing_score": 50,
             "max_mock_attempts": 3, "allow_review": "on"},
            organization=self.organization,
            organization_categories_only=True,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("primary_category", form.errors)
        self.assertNotIn("Global", [str(category) for category in form.fields["categories"].queryset])
