from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_shell_matches_practice_typography_and_filter_layout(self):
        root = Path(__file__).resolve().parents[2]

        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn('eyebrow.textContent = "PRACTICE"', express_ui)
        self.assertNotIn(
            'subtitle.textContent = "Strengthen your knowledge one question at a time."',
            express_ui,
        )
        self.assertIn("font-size: 1.5rem;", express_ui)
        self.assertIn("font-weight: 400;", express_ui)
        self.assertIn("min-height: 48px;", express_ui)
        self.assertIn("padding: 0 15px;", express_ui)
        self.assertIn("padding: 4px 15px 15px;", express_ui)
        self.assertIn("margin-bottom: 0 !important;", express_ui)
        self.assertIn('filterHint.textContent = "Click to expand"', shared_ui)
        self.assertIn("filterHint.hidden = false", shared_ui)
        self.assertNotIn('filterHint.textContent = ""', shared_ui)
        self.assertNotIn('filterHint.hidden = true', shared_ui)

    def test_express_uses_the_practice_question_layout(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('className = "practice-progress"', express_ui)
        self.assertIn('className = "practice-question-meta"', express_ui)
        self.assertIn('className = "practice-question-type"', express_ui)
        self.assertIn('className = "practice-question-text"', express_ui)
        self.assertIn('textContent = `Question #${', express_ui)
        self.assertIn('textContent = "Check Answer"', express_ui)
        self.assertIn('textContent = "Skip"', express_ui)
        self.assertIn('className = "practice-btn practice-btn-secondary"', express_ui)
        self.assertIn('className = "practice-btn practice-btn-primary"', express_ui)

    def test_express_hides_legacy_stats_and_timer_visuals(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('stats.style.display = "none"', express_ui)
        self.assertIn('timer.style.display = "none"', express_ui)
        self.assertIn('filterBody.style.maxHeight = "0px"', express_ui)


if __name__ == "__main__":
    unittest.main()
