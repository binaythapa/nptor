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

    def test_exam_preview_has_no_inline_style_block_or_duplicate_page_css(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")
        self.assertNotIn("<style>", template)
        self.assertNotIn("style=\"", template)

    def test_exam_preview_keeps_purchase_flow_and_sample_disclaimer(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_preview.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'payments:exam_checkout' exam.id %}", template)
        self.assertIn("{% url 'quiz:exam_start' exam.id %}", template)
        self.assertIn("Answers are intentionally not submitted or scored in preview mode.", template)


if __name__ == "__main__":
    unittest.main()
