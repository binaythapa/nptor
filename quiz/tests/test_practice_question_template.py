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

    def test_answer_choices_use_compact_layout(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice"
            / "_practice_question.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn('.practice-question-card .practice-options {', template)
        self.assertIn('gap: 7px;', template)
        self.assertIn('min-height: 46px;', template)
        self.assertIn('padding: 7px 10px;', template)
        self.assertIn('flex: 0 0 34px;', template)
        self.assertIn('width: 34px;', template)
        self.assertIn('height: 34px;', template)

    def test_question_number_uses_practice_sequence_not_database_id(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice"
            / "_practice_question.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("Question #{{ request.session.p_seen|length|add:\"1\" }}", template)
        self.assertNotIn("Question #{{ question.id }}", template)

    def test_answer_result_uses_practice_sequence_not_database_id(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice"
            / "_answer_result.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("Question #{{ request.session.p_seen|length|add:\"1\" }}", template)
        self.assertNotIn("Question #{{ question.id }}", template)

    def test_practice_express_uses_shared_practice_mode_navigation(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "practice_express"
            / "practice_express.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("{% static 'css/pages/practice.css' %}", template)
        self.assertIn("{% static 'css/pages/practice-mobile.css' %}", template)
        self.assertIn('class="practice-mode-nav"', template)
        self.assertIn('class="practice-mode"', template)
        self.assertIn('class="practice-mode active"', template)
        self.assertIn(">Basics</a>", template)
        self.assertIn(">Express</a>", template)
        self.assertIn(">Pro</a>", template)
        self.assertNotIn('class="practice-modes"', template)
        self.assertNotIn('class="practice-link"', template)


if __name__ == "__main__":
    unittest.main()
