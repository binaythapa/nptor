from pathlib import Path
from django.test import SimpleTestCase


class PracticeProgressUITests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_filter_can_be_fully_hidden_when_collapsed(self):
        css = (self.root / "static/css/pages/practice-mobile.css").read_text()
        script = (self.root / "static/js/pages/practice.js").read_text()

        self.assertIn('.practice-filter-body:not(.is-open)', css)
        self.assertIn('filterBody.hidden = !expanded', script)
        self.assertIn('filterToggle.setAttribute("aria-expanded"', script)

    def test_progress_is_updated_after_ajax_content_changes(self):
        script = (self.root / "static/js/pages/practice.js").read_text()

        self.assertIn("function updateProgress", script)
        self.assertIn("progress_done", script)
        self.assertIn("progress_total", script)
        self.assertIn("aria-valuenow", script)
        self.assertIn("practice-progress-bar", script)
