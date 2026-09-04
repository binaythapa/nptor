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

    def test_exam_review_keeps_changeable_option_controls(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_review.html").read_text(encoding="utf-8")

        self.assertIn('class="exam-review-option-marker"', template)
        self.assertIn('class="exam-review-option-input"', template)
        self.assertIn('type="radio"', template)
        self.assertIn('type="checkbox"', template)
        self.assertNotIn('type="hidden" name="question_', template)

    def test_exam_review_styles_are_scoped_and_support_changeable_options(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-review.css").read_text(encoding="utf-8")

        self.assertIn(".exam-review-page", css)
        self.assertIn(".exam-review-option", css)
        self.assertIn(".exam-review-option-input", css)
        self.assertIn(":checked", css)
        self.assertNotIn(".practice-", css)


if __name__ == "__main__":
    unittest.main()
