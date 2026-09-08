from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates/layouts/student/sidebar.html"


class StudentNavigationLabelTests(SimpleTestCase):
    def test_learning_navigation_replaces_courses_and_exams_label(self):
        html = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('<p class="menu-label">Learning</p>', html)
        self.assertNotIn("Courses &amp; Exams", html)
