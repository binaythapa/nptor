from pathlib import Path
import unittest


class PracticeExpressCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")
        cls.styles = (root / "static" / "css" / "pages" / "practice.css").read_text(encoding="utf-8")
        cls.template = (
            root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html"
        ).read_text(encoding="utf-8")

    def test_express_filter_uses_shared_practice_filter_contract(self):
        for text in (
            "normalizeExpressPracticeFilter",
            "initPracticeFilterCollapse",
            "practice-filter-panel",
            "practice-filter-header",
            "practice-filter-heading",
            "practice-filter-body",
            "practice-filter-grid",
            "practice-filter-field",
            "practice-select-wrap",
            'id=\"filterHint\"',
        ):
            self.assertIn(text, self.shared_ui)

        for text in (
            "min-height: 48px",
            "padding: 0 15px",
            "font-size: 0.84rem",
            "font-weight: 800",
            "gap: 13px",
            "padding: 0 15px 15px",
            "min-height: 39px",
            "font-size: 0.8rem",
        ):
            self.assertIn(text, self.styles)

    def test_express_filter_is_the_only_practice_block_restyled(self):
        start = self.shared_ui.index("function normalizeExpressPracticeFilter()")
        end = self.shared_ui.index("normalizeExpressPracticeFilter();", start)
        filter_code = self.shared_ui[start:end]

        self.assertNotIn("practice-page", filter_code)
        self.assertNotIn("practice-question-card", filter_code)
        self.assertNotIn("practice-progress", filter_code)
        self.assertNotIn("practice-mode", filter_code)

    def test_express_filter_keeps_existing_toggle_behavior(self):
        self.assertIn('onclick="toggleFilters()"', self.template)
        self.assertIn('id="filterBody"', self.template)
        self.assertIn("function toggleFilters()", self.template)
        self.assertIn('localStorage.setItem("expressFilterExpanded"', self.template)


if __name__ == "__main__":
    unittest.main()
