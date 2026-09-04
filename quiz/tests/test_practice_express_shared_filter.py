from pathlib import Path
import unittest


class PracticeExpressSharedFilterTests(unittest.TestCase):
    def test_express_filter_does_not_override_legacy_layout_with_shared_mapper(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertNotIn("function initExpressFilterLayout()", shared_ui)
        self.assertNotIn("initExpressFilterLayout();", shared_ui)

    def test_express_filter_uses_practice_filter_structure_and_state(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

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
            self.assertIn(marker, shared_ui)

        self.assertIn('filter.classList.add("practice-panel", "practice-filter-panel")', shared_ui)
        self.assertIn('filterToggle.setAttribute("aria-expanded"', shared_ui)
        self.assertIn('filterBody.classList.toggle("is-open", expanded)', shared_ui)
        self.assertIn('localStorage.setItem("practiceFilterExpanded", expanded ? "1" : "0")', shared_ui)

    def test_express_filter_matches_practice_collapsed_header(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('toggle.className = "practice-filter-header"', shared_ui)
        self.assertIn('toggle.setAttribute("aria-controls", "filterBody")', shared_ui)
        self.assertIn('<span>Filters</span>', shared_ui)
        self.assertIn('<small id="filterHint">Click to expand</small>', shared_ui)
        self.assertIn('<span id="filterToggleIcon" class="practice-filter-arrow"', shared_ui)
        self.assertIn('.practice-express-filter > div:first-child', express_ui)
        self.assertIn('display: flex;', express_ui)
        self.assertIn('justify-content: space-between;', express_ui)
        self.assertIn('.practice-express-filter .practice-filter-icon', express_ui)
        self.assertIn('display: none !important;', express_ui)

    def test_express_filter_removes_legacy_inline_collapse_styles(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('body.style.maxHeight = ""', shared_ui)
        self.assertIn('body.style.padding = ""', shared_ui)
        self.assertIn('body.style.transition = ""', shared_ui)
        self.assertIn('body.className = "practice-filter-body"', shared_ui)

    def test_express_filter_uses_grid_row_collapse_like_practice(self):
        root = Path(__file__).resolve().parents[2]
        practice_css = (root / "static" / "css" / "pages" / "practice.css").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('grid-template-rows:0fr;', practice_css.replace(" ", ""))
        self.assertIn('filterBody.classList.toggle("is-open", expanded)', shared_ui)
        self.assertIn('body.className = "practice-filter-body"', shared_ui)

    def test_express_filter_reapplies_state_after_legacy_domcontentloaded_handler(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('setTimeout(() => {', shared_ui)
        self.assertIn('filterBody.style.maxHeight = ""', shared_ui)
        self.assertIn('setFilterState(localStorage.getItem("practiceFilterExpanded") === "1")', shared_ui)

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

    def test_express_root_box_is_removed_so_child_blocks_are_independent(self):
        root = Path(__file__).resolve().parents[2]
        express_ui = (root / "static" / "js" / "practice-express-ui.js").read_text(encoding="utf-8")

        self.assertIn('page.classList.remove("box")', express_ui)
        self.assertIn('.practice-express-page > .box {', express_ui)


if __name__ == "__main__":
    unittest.main()
