from pathlib import Path
from django.test import SimpleTestCase


class PracticeResultLayoutTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_next_question_action_is_inside_result_block(self):
        template = (
            self.root / "templates/quiz/student/practice/_answer_result.html"
        ).read_text()

        result_start = template.index('class="practice-result')
        result_end = template.index('</div>', result_start) + len('</div>')
        result_block = template[result_start:result_end]

        self.assertIn('data-practice-next', result_block)
        self.assertIn('Try Next Question', result_block)

    def test_result_block_uses_side_by_side_action_layout(self):
        css = (self.root / "static/css/pages/practice-mobile.css").read_text()

        self.assertIn('.practice-result.with-next-action', css)
        self.assertIn('.practice-result-content', css)
        self.assertIn('.practice-result-next', css)
        self.assertIn('justify-content:space-between', css)
