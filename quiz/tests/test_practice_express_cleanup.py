from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_shell_removes_unnecessary_heading_and_filter_hint(self):
        script_path = (
            Path(__file__).resolve().parents[2]
            / "static"
            / "js"
            / "practice-express-ui.js"
        )
        script = script_path.read_text(encoding="utf-8")

        self.assertNotIn('eyebrow.textContent = "PRACTICE"', script)
        self.assertNotIn(
            'subtitle.textContent = "Strengthen your knowledge one question at a time."',
            script,
        )
        self.assertIn('filterHint.textContent = ""', script)
        self.assertIn('filterHint.hidden = true', script)


if __name__ == "__main__":
    unittest.main()
