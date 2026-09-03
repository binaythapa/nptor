from pathlib import Path
from django.test import SimpleTestCase


class PracticeLayoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_practice_uses_express_parity_stylesheet(self):
        template = (self.root / "templates/quiz/student/practice/practice.html").read_text()
        css = (self.root / "static/css/pages/practice-express-parity.css").read_text()

        self.assertIn("practice-express-parity.css", template)
        self.assertIn(".practice-page", css)
        self.assertIn(".practice-mode.active", css)
        self.assertIn(".practice-filter-panel", css)
        self.assertIn(".practice-question-card", css)

    def test_parity_styles_keep_compact_desktop_proportions(self):
        css = (self.root / "static/css/pages/practice-express-parity.css").read_text()

        self.assertIn("max-width: 1100px", css)
        self.assertIn("font-size: 1.25rem", css)
        self.assertIn("min-height: 34px", css)
        self.assertIn("padding: 15px", css)
