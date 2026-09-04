from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_filter_reuses_practice_filter_properties_only(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('practice.css', express_ui)
        self.assertIn('practice-filter-panel', express_ui)
        self.assertIn('practice-filter-header', express_ui)
        self.assertIn('practice-filter-heading', express_ui)
        self.assertIn('practice-filter-body', express_ui)
        self.assertIn('practice-filter-grid', express_ui)
        self.assertIn('practice-filter-field', express_ui)
        self.assertIn('practice-select-wrap', express_ui)
        self.assertIn('filterHint.tagName', express_ui)
        self.assertNotIn('practice-page', express_ui)
        self.assertNotIn('practice-question-card', express_ui)
        self.assertNotIn('practice-progress', express_ui)

    def test_express_filter_does_not_change_question_or_stats_layout(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('classList.add("practice-express-filter")', express_ui)
        self.assertIn('classList.add("practice-express-stats")', express_ui)
        self.assertIn('classList.add("practice-question-card")', express_ui)
        self.assertIn('classList.add("practice-options")', express_ui)

    def test_express_filter_keeps_existing_toggle_behavior(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html").read_text(encoding="utf-8")

        self.assertIn('onclick="toggleFilters()"', template)
        self.assertIn('id="filterBody"', template)
        self.assertIn('function toggleFilters()', template)
        self.assertIn('localStorage.setItem("expressFilterExpanded"', template)


if __name__ == "__main__":
    unittest.main()
