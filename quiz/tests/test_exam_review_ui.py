from pathlib import Path
import unittest


class ExamReviewUITests(unittest.TestCase):
    def test_exam_review_uses_dedicated_stylesheet_and_scoped_markup(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_review.html").read_text(encoding="utf-8")

        self.assertIn("css/pages/exam-review.css", template)
        self.assertIn('class="exam-review-page"', template)
        self.assertIn('class="exam-review-card"', template)
        self.assertIn('class="exam-review-option"', template)
        self.assertNotIn("<style>", template)

    def test_exam_review_removes_visible_native_option_controls(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_review.html").read_text(encoding="utf-8")

        self.assertIn('class="exam-review-option-marker"', template)
        self.assertIn('type="hidden"', template)
        self.assertNotIn('type="radio"', template)
        self.assertNotIn('type="checkbox"', template)

    def test_exam_review_styles_are_scoped(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-review.css").read_text(encoding="utf-8")

        self.assertIn(".exam-review-page", css)
        self.assertIn(".exam-review-option", css)
        self.assertNotIn(".practice-", css)


if __name__ == "__main__":
    unittest.main()
