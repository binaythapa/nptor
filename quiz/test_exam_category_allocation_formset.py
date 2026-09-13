from django.test import TestCase

from organizations.models import Organization
from quiz.forms import ExamCategoryAllocationFormSet
from quiz.models import Category, Exam


class ExamCategoryAllocationFormSetTests(TestCase):
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
            name="General",
            slug="general",
        )

    def test_organization_formset_exposes_only_organization_categories(self):
        exam = Exam(organization=self.organization, title="School Exam", question_count=20, duration_seconds=600)
        category_queryset = Category.objects.filter(organization=self.organization, is_active=True)
        formset = ExamCategoryAllocationFormSet(instance=exam, category_queryset=category_queryset)

        self.assertEqual(
            set(formset.forms[0].fields["category"].queryset.values_list("id", flat=True)),
            {self.org_category.pk},
        )

    def test_organization_formset_rejects_other_organization_category(self):
        exam = Exam(organization=self.organization, title="School Exam", question_count=20, duration_seconds=600)
        category_queryset = Category.objects.filter(organization=self.organization, is_active=True)
        formset = ExamCategoryAllocationFormSet(
            {
                "allocations-TOTAL_FORMS": "1",
                "allocations-INITIAL_FORMS": "0",
                "allocations-MIN_NUM_FORMS": "0",
                "allocations-MAX_NUM_FORMS": "1000",
                "allocations-0-category": str(self.other_category.pk),
                "allocations-0-percentage": "50",
                "allocations-0-fixed_count": "",
                "allocations-0-DELETE": "",
            },
            instance=exam,
            category_queryset=category_queryset,
        )

        self.assertFalse(formset.is_valid())
        self.assertIn("category", formset.forms[0].errors)

    def test_global_exam_can_allocate_global_category(self):
        exam = Exam(title="Global Exam", question_count=20, duration_seconds=600)
        category_queryset = Category.objects.filter(is_active=True)
        formset = ExamCategoryAllocationFormSet(
            {
                "allocations-TOTAL_FORMS": "1",
                "allocations-INITIAL_FORMS": "0",
                "allocations-MIN_NUM_FORMS": "0",
                "allocations-MAX_NUM_FORMS": "1000",
                "allocations-0-category": str(self.global_category.pk),
                "allocations-0-percentage": "50",
                "allocations-0-fixed_count": "",
                "allocations-0-DELETE": "",
            },
            instance=exam,
            category_queryset=category_queryset,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
