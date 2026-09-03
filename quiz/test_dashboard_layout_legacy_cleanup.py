from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates/quiz/student/student_dashboard.html"
CSS = ROOT / "static/css/pages/dashboard_learning_hub.css"


class StudentDashboardLegacyLayoutTests(SimpleTestCase):
    def test_compact_hub_replaces_the_old_large_resource_sections(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")

        self.assertNotIn("My Courses", html)
        self.assertNotIn("My Exam Tracks", html)
        self.assertIn("My Learning", html)
        self.assertIn(".dashboard-learning-card", css)
