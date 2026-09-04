from pathlib import Path
import unittest


class ExamPreviewUITests(unittest.TestCase):
    def test_exam_preview_uses_dedicated_compact_exam_structure(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")

        for marker in (
            "exam-preview-page",
            "exam-preview-header",
            "exam-preview-meta",
            "exam-preview-actions",
            "exam-preview-section",
            "exam-preview-question-card",
            "exam-preview-question-number",
            "exam-preview-options",
        ):
            self.assertIn(marker, template)

    def test_exam_preview_has_no_inline_styling(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")
        self.assertNotIn("<style>", template)
        self.assertNotIn("style=\"", template)

    def test_exam_preview_loads_dedicated_stylesheet(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")
        stylesheet = root / "static" / "css" / "pages" / "exam-preview.css"
        self.assertTrue(stylesheet.exists())
        self.assertIn("css/pages/exam-preview.css", template)

    def test_exam_preview_keeps_purchase_flow_and_sample_disclaimer(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'payments:exam_checkout' exam.id %}", template)
        self.assertIn("{% url 'quiz:exam_start' exam.id %}", template)
        self.assertIn("Answers are intentionally not submitted or scored in preview mode.", template)

    def test_exam_preview_styles_are_scoped_to_exam_preview(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-preview.css").read_text(encoding="utf-8")
        self.assertIn(".exam-preview-page", css)
        self.assertIn(".exam-preview-question-card", css)
        self.assertNotIn(".practice-", css)


if __name__ == "__main__":
    unittest.main()
