from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from quiz.services.learning_catalog import _resource_item


class LearningMarketplaceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "quiz"
            / "student"
            / "learning_marketplace.html"
        ).read_text(encoding="utf-8")

    def test_resource_cards_have_clear_product_hierarchy(self):
        for hook in (
            'class="resource-type"',
            'class="resource-title"',
            'class="resource-metrics"',
            'class="resource-pricing"',
            'class="resource-access-badge"',
            'class="resource-action"',
            'class="shortlist-button',
        ):
            self.assertIn(hook, self.template)

    def test_catalog_exposes_course_track_and_exam_presentation_metadata(self):
        course = SimpleNamespace(level="beginner")
        exam = SimpleNamespace(duration_seconds=5400)
        track = SimpleNamespace(exams=SimpleNamespace(all=lambda: []))

        course_item = _resource_item("course", course)
        exam_item = _resource_item("exam", exam)
        track_item = _resource_item("track", track)

        self.assertEqual(course_item["presentation_type"], "course")
        self.assertEqual(exam_item["duration_minutes"], 90)
        self.assertEqual(track_item["exam_count"], 0)
        self.assertIn("pricing_label", course_item)
        self.assertIn("access_label", course_item)

    def test_access_state_language_is_explicit(self):
        for text in (
            "Free",
            "Premium",
            "Purchased",
            "Preview",
            "Locked",
            "You have access",
        ):
            self.assertIn(text, self.template)

    def test_track_cards_explain_bundle_contents(self):
        for hook in (
            "exams included",
            "questions",
            "Structured certification preparation",
        ):
            self.assertIn(hook, self.template)
