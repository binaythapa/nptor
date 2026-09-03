from pathlib import Path
from django.test import SimpleTestCase


class PracticeProgressUITests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_filter_state_is_fully_collapsed_and_accessible(self):
        template = (self.root / "templates/quiz/student/practice/practice.html").read_text()

        self.assertIn('id="filterBody"', template)
        self.assertIn('body.hidden = !expanded', template)
        self.assertIn('body.style.display = expanded ? "grid" : "none"', template)
        self.assertIn('toggle.setAttribute("aria-expanded", String(expanded))', template)

    def test_progress_is_synchronized_after_next_or_skip_ajax(self):
        template = (self.root / "templates/quiz/student/practice/practice.html").read_text()

        self.assertIn('function updateProgress(increment)', template)
        self.assertIn('requestUrl === nextUrl || requestUrl === skipUrl', template)
        self.assertIn('updateProgress(1)', template)
        self.assertIn('aria-valuenow', template)
        self.assertIn('el.bar.style.width = percent + "%"', template)
