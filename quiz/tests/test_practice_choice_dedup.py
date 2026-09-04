from pathlib import Path
import unittest


class PracticeChoiceDedupTests(unittest.TestCase):
    def test_global_choice_css_suppresses_duplicate_pseudo_labels(self):
        css_path = (
            Path(__file__).resolve().parents[2]
            / "static"
            / "css"
            / "exam_timer.css"
        )
        css = css_path.read_text(encoding="utf-8")

        self.assertIn(".practice-option::before", css)
        self.assertIn(".choice-item::before", css)
        self.assertIn("content: none !important", css)
        self.assertIn("display: none !important", css)


if __name__ == "__main__":
    unittest.main()
