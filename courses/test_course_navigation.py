from pathlib import Path

from django.test import SimpleTestCase


class CourseNavigationContractTests(SimpleTestCase):
    def test_progress_service_exposes_smart_next_lesson_helper(self):
        source = (
            Path(__file__).resolve().parent / "services" / "progress.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def get_next_learning_lesson(user, course, lesson):", source)
        self.assertIn("exclude(id__in=completed_ids)", source)

    def test_player_uses_completion_aware_navigation_hooks(self):
        template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_player.html"
        ).read_text(encoding="utf-8")
        for hook in (
            'data-completed="{% if not is_preview and lesson_progress.completed %}true{% else %}false{% endif %}"',
            "next-incomplete",
            "completed",
            "Continue Learning",
            "NEXT LESSON",
            "Course Complete",
        ):
            self.assertIn(hook, template)

    def test_navigation_keeps_preview_and_mobile_hooks(self):
        template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "course_player.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="lessonPrev"', template)
        self.assertIn('id="lessonNext"', template)
        self.assertIn("preview=1", template)
