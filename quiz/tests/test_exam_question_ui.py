from pathlib import Path
import unittest


class ExamQuestionUITests(unittest.TestCase):
    def test_exam_question_template_uses_dedicated_stylesheet_and_marked_options(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_question.html").read_text(encoding="utf-8")

        self.assertIn("css/pages/exam-question.css", template)
        self.assertIn("class=\"exam-question-page\"", template)
        self.assertIn("class=\"exam-options\"", template)
        self.assertIn("class=\"option-marker\"", template)
        self.assertIn("class=\"option-text\"", template)
        self.assertNotIn("<style>", template)

    def test_exam_question_keeps_direct_expiry_submission(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_question.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'quiz:exam_submit' user_exam_id=user_exam.id %}", template)
        self.assertIn("form.submit();", template)

    def test_exam_question_styles_are_scoped(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-question.css").read_text(encoding="utf-8")
        self.assertIn(".exam-question-page", css)
        self.assertIn(".exam-header", css)
        self.assertIn(".option-marker", css)
        self.assertNotIn(".practice-", css)


if __name__ == "__main__":
    unittest.main()
