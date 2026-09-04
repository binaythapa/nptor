from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    def test_express_filter_uses_practice_filter_properties_only(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn("initExpressFilterLayout", shared_ui)
        self.assertIn('practice-filter-panel', shared_ui)
        self.assertIn('practice-filter-header', shared_ui)
        self.assertIn('practice-filter-heading', shared_ui)
        self.assertIn('practice-filter-body', shared_ui)
        self.assertIn('practice-filter-grid', shared_ui)
        self.assertIn('practice-filter-field', shared_ui)
        self.assertIn('practice-select-wrap', shared_ui)
        self.assertIn('filterHint.tagName', shared_ui)

        self.assertIn('min-height: 48px', shared_ui)
        self.assertIn('padding: 0 15px', shared_ui)
        self.assertIn('font-size: 0.84rem', shared_ui)
        self.assertIn('font-weight: 800', shared_ui)
        self.assertIn('gap: 13px', shared_ui)
        self.assertIn('padding: 0 15px 15px', shared_ui)
        self.assertIn('min-height: 39px', shared_ui)
        self.assertIn('font-size: 0.8rem', shared_ui)

    def test_express_filter_is_the_only_practice_block_restyled(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        start = shared_ui.index('function initExpressFilterLayout()')
        end = shared_ui.index('initExpressFilterLayout();', start)
        filter_code = shared_ui[start:end]

        self.assertNotIn('practice-page', filter_code)
        self.assertNotIn('practice-question-card', filter_code)
        self.assertNotIn('practice-progress', filter_code)
        self.assertNotIn('practice-mode', filter_code)

    def test_express_filter_keeps_existing_toggle_behavior(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html").read_text(encoding="utf-8")

        self.assertIn('onclick="toggleFilters()"', template)
        self.assertIn('id="filterBody"', template)
        self.assertIn('function toggleFilters()', template)
        self.assertIn('localStorage.setItem("expressFilterExpanded"', template)


if __name__ == "__main__":
    unittest.main()
