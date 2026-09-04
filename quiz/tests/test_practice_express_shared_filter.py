from pathlib import Path
import unittest


class PracticeExpressSharedFilterTests(unittest.TestCase):
    def test_express_filter_does_not_override_legacy_layout_with_shared_mapper(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn("function initExpressFilterLayout()", shared_ui)
        self.assertNotIn("initExpressFilterLayout();", shared_ui)

    def test_express_filter_uses_shared_practice_filter_classes_at_runtime(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        for marker in (
            'practice-filter-panel',
            'practice-filter-header',
            'practice-filter-heading',
            'practice-filter-arrow',
            'practice-filter-body',
            'practice-filter-form',
            'practice-filter-grid',
            'practice-filter-field',
            'practice-select-wrap',
        ):
            self.assertIn(marker, express_ui)

        self.assertIn("practice.css", express_ui)
        self.assertIn('filterToggle.setAttribute("aria-expanded"', express_ui)

    def test_express_filter_uses_the_same_practice_filter_state_key_and_logic(self):
        root = Path(__file__).resolve().parents[2]
        practice_js = (root / "static" / "js" / "pages" / "practice.js").read_text(encoding="utf-8")
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('"practiceFilterExpanded"', practice_js)
        self.assertIn('"practiceFilterExpanded"', express_ui)
        self.assertIn('classList.toggle("is-open", expanded)', express_ui)
        self.assertIn('localStorage.setItem("practiceFilterExpanded", expanded ? "1" : "0")', express_ui)

    def test_express_filter_has_no_legacy_inline_toggle(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "practice_express" / "practice_express.html").read_text(encoding="utf-8")

        self.assertNotIn('onclick="toggleFilters()"', template)
        self.assertNotIn("function toggleFilters()", template)
        self.assertNotIn("expressFilterExpanded", template)

    def test_shared_filter_collapse_is_initialized_once(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")
        practice_js = (root / "static" / "js" / "pages" / "practice.js").read_text(encoding="utf-8")

        self.assertIn("function initPracticeFilterCollapse()", shared_ui)
        self.assertIn("data.practiceFilterInitialized", practice_js)
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
