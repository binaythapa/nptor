from pathlib import Path

from django.test import SimpleTestCase


class CourseNavigationContractTests(SimpleTestCase):
    def test_progress_service_exposes_smart_next_lesson_helper(self):
        source = (
            Path(__file__).resolve().parent / "services" / "progress.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def get_next_learning_lesson(user, course, lesson):", source)
        self.assertIn("exclude(id__in=completed_ids)", source)

    def test_player_uses_smart_navigation_context(self):
        template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_player.html"
        ).read_text(encoding="utf-8")
        self.assertIn("next_learning_lesson", template)
        self.assertIn("Continue Learning", template)
        self.assertIn("NEXT LESSON", template)

    def test_player_view_uses_smart_navigation_helper(self):
        source = (
            Path(__file__).resolve().parent / "views" / "student_views.py"
        ).read_text(encoding="utf-8")
        self.assertIn("get_next_learning_lesson", source)
        self.assertIn("next_learning_lesson =", source)
