from pathlib import Path
import unittest


class PracticeQuestionTemplateTests(unittest.TestCase):
    def test_answer_choices_include_aligned_letter_marker_and_content(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice"
            / "_practice_question.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn('{% cycle "A" "B" "C" "D" as choice_letter %}', template)
        self.assertIn('class="practice-option-marker"', template)
        self.assertIn('class="practice-option-text"', template)
        self.assertIn('{{ choice_letter }}', template)


if __name__ == "__main__":
    unittest.main()
