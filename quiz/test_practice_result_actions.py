from pathlib import Path
from django.test import SimpleTestCase


class PracticeResultActionTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_answer_result_has_no_redundant_practice_action(self):
        template = (
            self.root
            / "templates/quiz/student/practice/_answer_result.html"
        ).read_text()

        self.assertNotIn(
            "class=\"practice-btn practice-btn-secondary\"",
            template,
        )
        self.assertIn("data-practice-next", template)
