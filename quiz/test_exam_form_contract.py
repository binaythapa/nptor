from django.test import SimpleTestCase

from .forms import ExamForm


class ExamFormContractTests(SimpleTestCase):
    def test_exam_form_exposes_all_user_managed_exam_fields(self):
        expected_fields = {
            "title",
            "organization",
            "primary_category",
            "categories",
            "question_count",
            "duration_seconds",
            "level",
            "passing_score",
            "is_published",
            "max_mock_attempts",
            "allow_review",
        }

        self.assertEqual(set(ExamForm.Meta.fields), expected_fields)
        self.assertNotIn("subscription_plans", ExamForm.Meta.fields)
        self.assertNotIn("created_at", ExamForm.Meta.fields)
        self.assertNotIn("updated_at", ExamForm.Meta.fields)
        self.assertNotIn("created_by", ExamForm.Meta.fields)
