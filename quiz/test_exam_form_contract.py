from django.template.loader import get_template
from django.test import SimpleTestCase

from .forms import ExamForm
from .search_widgets import SearchableModelChoiceWidget, SearchableModelMultipleChoiceWidget


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

    def test_category_fields_use_server_side_search_widgets(self):
        self.assertIsInstance(
            ExamForm.Meta.widgets["primary_category"],
            SearchableModelChoiceWidget,
        )
        self.assertIsInstance(
            ExamForm.Meta.widgets["categories"],
            SearchableModelMultipleChoiceWidget,
        )
        self.assertEqual(
            ExamForm.Meta.widgets["primary_category"].attrs["data-autocomplete-scope"],
            "categories",
        )
        self.assertEqual(
            ExamForm.Meta.widgets["categories"].attrs["data-autocomplete-scope"],
            "categories",
        )

    def test_exam_admin_template_renders_all_user_managed_exam_fields(self):
        source = get_template("quiz/student/subscription/exam_form.html").template.source

        for field_name in ExamForm.Meta.fields:
            self.assertIn(
                f"form.{field_name}",
                source,
                msg=f"Exam admin template is missing {field_name}.",
            )

        self.assertIn("admin_exam_selector.js", source)
        self.assertIn("admin_single_exam_selector.js", source)
        self.assertNotIn("form.subscription_plans", source)
