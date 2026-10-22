from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates/quiz/student/student_dashboard.html"
CSS = ROOT / "static/css/pages/dashboard_learning_hub.css"


class StudentDashboardLayoutTests(SimpleTestCase):
    def test_dashboard_uses_compact_learning_hub_sections(self):
        html = TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('data-dashboard-filter="all"', html)
        self.assertIn('data-dashboard-filter="courses"', html)
        self.assertIn('data-dashboard-filter="exams"', html)
        self.assertIn('data-dashboard-filter="tracks"', html)
        self.assertIn("data-dashboard-search", html)
        self.assertIn("dashboard-continue", html)
        self.assertIn("dashboard-learning-grid", html)
        self.assertIn('data-learning-type="course"', html)
        self.assertIn('data-learning-type="exam"', html)
        self.assertIn('data-learning-type="track"', html)
        self.assertIn("dashboard_learning_hub.css", html)

    def test_compact_hub_replaces_old_resource_sections(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn("My Courses", html)
        self.assertNotIn("My Exam Tracks", html)
        self.assertIn("My Learning", html)

    def test_dashboard_has_compact_responsive_styles(self):
        css = CSS.read_text(encoding="utf-8")

        self.assertIn(".dashboard-learning-toolbar", css)
        self.assertIn(".dashboard-learning-grid", css)
        self.assertIn(".dashboard-learning-card", css)
        self.assertIn(".dashboard-continue", css)
        self.assertTrue(
            "@media (max-width: 760px)" in css or "@media (max-width:760px)" in css
        )
