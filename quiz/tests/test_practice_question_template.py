from pathlib import Path
import unittest


class PracticeQuestionTemplateTests(unittest.TestCase):
    def test_answer_choices_render_one_visible_letter_marker(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice"
            / "_practice_question.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertEqual(template.count('class="practice-option-marker"'), 1)
        self.assertIn('class="practice-option-marker practice-option-marker-checkbox"', template)
        self.assertEqual(template.count('class="practice-option-text"'), 2)
        self.assertEqual(template.count('{% if forloop.counter == 1 %}A{% elif forloop.counter == 2 %}B{% elif forloop.counter == 3 %}C{% elif forloop.counter == 4 %}D{% endif %}'), 2)
        self.assertNotIn('forloop.counter0|add:65', template)
        self.assertNotIn('{% cycle "A" "B" "C" "D" %}', template)
        self.assertNotIn('{% cycle "A" "B" "C" "D" as choice_letter_single %}', template)
        self.assertNotIn('{% cycle "A" "B" "C" "D" as choice_letter_multi %}', template)
        self.assertNotIn('{{ choice_letter_single }}', template)
        self.assertNotIn('{{ choice_letter_multi }}', template)


if __name__ == "__main__":
    unittest.main()
