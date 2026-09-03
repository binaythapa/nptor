from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates/quiz/student/student_dashboard.html"
CSS = ROOT / "static/css/pages/dashboard_learning_hub.css"


class StudentDashboardLearningHubTests(SimpleTestCase):
    def test_dashboard_has_compact_learning_resource_controls(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        for marker in (
            'data-dashboard-filter="all"',
            'data-dashboard-filter="courses"',
            'data-dashboard-filter="exams"',
            'data-dashboard-filter="tracks"',
            "data-dashboard-search",
            "dashboard-continue",
            "dashboard-learning-grid",
            'data-learning-type="course"',
            'data-learning-type="exam"',
            'data-learning-type="track"',
            "dashboard_learning_hub.css",
        ):
            self.assertIn(marker, html)

    def test_dashboard_learning_hub_is_compact_and_responsive(self):
        css = CSS.read_text(encoding="utf-8")
        for marker in (
            ".dashboard-learning-toolbar",
            ".dashboard-learning-grid",
            ".dashboard-learning-card",
            ".dashboard-continue",
            "@media (max-width: 760px)",
        ):
            self.assertIn(marker, css)
