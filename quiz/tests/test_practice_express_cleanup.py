from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_shell_removes_unnecessary_heading_and_filter_hint(self):
        root = Path(__file__).resolve().parents[2]

        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn('eyebrow.textContent = "PRACTICE"', express_ui)
        self.assertNotIn(
            'subtitle.textContent = "Strengthen your knowledge one question at a time."',
            express_ui,
        )
        self.assertIn('filterHint.textContent = ""', shared_ui)
        self.assertIn('filterHint.hidden = true', shared_ui)


if __name__ == "__main__":
    unittest.main()
