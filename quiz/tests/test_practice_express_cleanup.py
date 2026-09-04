from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_shell_removes_unnecessary_heading_text(self):
        root = Path(__file__).resolve().parents[2]

        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn('eyebrow.textContent = "PRACTICE"', express_ui)
        self.assertNotIn(
            'subtitle.textContent = "Strengthen your knowledge one question at a time."',
            express_ui,
        )
        self.assertNotIn('filterHint.textContent = ""', shared_ui)
        self.assertNotIn('filterHint.hidden = true', shared_ui)

    def test_express_question_text_matches_practice_scale(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn("font-size: 1.05rem;", express_ui)
        self.assertIn("font-weight: 400;", express_ui)

    def test_express_filter_keeps_expand_hint(self):
        root = Path(__file__).resolve().parents[2]
        express_template = (
            root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html"
        ).read_text(encoding="utf-8")

        self.assertIn('(Expand)', express_template)


if __name__ == "__main__":
    unittest.main()
