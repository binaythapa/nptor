from pathlib import Path
import unittest


class PracticeExpressSharedFilterTests(unittest.TestCase):
    def test_express_filter_does_not_override_legacy_layout_with_shared_mapper(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn("function initExpressFilterLayout()", shared_ui)
        self.assertNotIn("initExpressFilterLayout();", shared_ui)

    def test_express_filter_is_not_forced_into_practice_grid_classes(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn('classList.add("practice-filter-panel")', shared_ui)
        self.assertNotIn('classList.add("practice-filter-body")', shared_ui)
        self.assertNotIn('classList.add("practice-filter-grid")', shared_ui)
        self.assertNotIn('classList.remove("practice-express-filter", "box", "mb-3", "p-3")', shared_ui)

    def test_express_filter_uses_the_shared_practice_markup_and_styles(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html").read_text(encoding="utf-8")
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        for marker in (
            'class="practice-panel practice-filter-panel"',
            'id="filterToggle" class="practice-filter-header"',
            'class="practice-filter-heading"',
            'class="practice-filter-arrow"',
            'id="filterBody" class="practice-filter-body"',
            'class="practice-filter-form"',
            'class="practice-filter-grid"',
            'class="practice-filter-field"',
            'class="practice-select-wrap"',
        ):
            self.assertIn(marker, template)

        self.assertIn("css/pages/practice.css", template)
        self.assertNotIn("onclick=\"toggleFilters()\"", template)
        self.assertNotIn("function toggleFilters()", template)
        self.assertNotIn("expressFilterExpanded", template)
        self.assertNotIn("practice-express-filter", express_ui)

    def test_express_filter_uses_the_same_practice_filter_state_key(self):
        root = Path(__file__).resolve().parents[2]
        practice_js = (root / "static" / "js" / "pages" / "practice.js").read_text(encoding="utf-8")
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('"practiceFilterExpanded"', practice_js)
        self.assertIn('"practiceFilterExpanded"', express_ui)
        self.assertIn('classList.toggle(\n            "is-open",', express_ui)

    def test_express_filter_has_no_legacy_compatibility_hook(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn("initExpressFilterCollapseCompatibility", shared_ui)

    def test_express_page_shell_is_visual_wrapper_not_a_shared_card(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        marker = ".practice-express-page {"
        start = express_ui.index(marker)
        end = express_ui.index("}", start)
        shell_rule = express_ui[start:end]

        self.assertIn("background: transparent;", shell_rule)
        self.assertIn("border: 0;", shell_rule)
        self.assertIn("box-shadow: none;", shell_rule)


if __name__ == "__main__":
    unittest.main()
