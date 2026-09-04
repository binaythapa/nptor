from pathlib import Path
import unittest


class ExamLockedUITests(unittest.TestCase):
    def test_exam_locked_template_exists_and_is_scoped(self):
        root = Path(__file__).resolve().parents[2]
        template_path = root / "templates" / "quiz" / "student" / "exam" / "exam_locked.html"

        self.assertTrue(template_path.exists())
        template = template_path.read_text(encoding="utf-8")
        self.assertIn("class=\"exam-locked-page\"", template)
        self.assertIn("exam_locked", template)
        self.assertIn("{% url 'quiz:exam_list' %}", template)

    def test_exam_locked_template_has_no_inline_styles(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_locked.html").read_text(encoding="utf-8")
        self.assertNotIn("<style>", template)
        self.assertNotIn("style=\"", template)

    def test_exam_locked_template_loads_dedicated_stylesheet(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_locked.html").read_text(encoding="utf-8")
        stylesheet = root / "static" / "css" / "pages" / "exam-locked.css"
        self.assertTrue(stylesheet.exists())
        self.assertIn("css/pages/exam-locked.css", template)

    def test_exam_locked_styles_are_scoped(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-locked.css").read_text(encoding="utf-8")
        self.assertIn(".exam-locked-page", css)
        self.assertNotIn(".practice-", css)


if __name__ == "__main__":
    unittest.main()
