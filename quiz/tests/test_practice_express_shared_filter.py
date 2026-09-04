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

        self.assertIn("css/pages/practice.css", shared_ui)
        self.assertIn('filterToggle.setAttribute("aria-expanded"', shared_ui)

    def test_express_filter_uses_the_same_practice_filter_state_key_and_logic(self):
        root = Path(__file__).resolve().parents[2]
        practice_js = (root / "static" / "js" / "pages" / "practice.js").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('"practiceFilterExpanded"', practice_js)
        self.assertIn('"practiceFilterExpanded"', shared_ui)
        self.assertIn('filterBody.classList.toggle("is-open", expanded)', shared_ui)
        self.assertIn('localStorage.setItem("practiceFilterExpanded", expanded ? "1" : "0")', shared_ui)

    def test_express_filter_replaces_legacy_dom_with_shared_structure(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('filter.classList.remove("box", "mb-3", "p-3")', shared_ui)
        self.assertIn('filter.classList.add("practice-panel", "practice-filter-panel")', shared_ui)
        self.assertIn('body.replaceChildren(form)', shared_ui)
        self.assertIn('filter.replaceChildren(toggle, body)', shared_ui)
        self.assertIn('body.style.maxHeight = ""', shared_ui)
        self.assertIn('body.style.padding = ""', shared_ui)
        self.assertIn('body.style.transition = ""', shared_ui)

    def test_express_filter_keeps_legacy_select_ids_for_existing_express_logic(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('const domainSelect = filter.querySelector("#domainSelect")', shared_ui)
        self.assertIn('const categorySelect = filter.querySelector("#categorySelect")', shared_ui)
        self.assertIn('const difficultySelect = filter.querySelector("#difficultySelect")', shared_ui)
        self.assertNotIn('select.id = id;', shared_ui)
        self.assertNotIn('select.name = id.replace("practice-", "");', shared_ui)

    def test_express_filter_uses_grid_row_collapse_like_practice(self):
        root = Path(__file__).resolve().parents[2]
        practice_css = (root / "static" / "css" / "pages" / "practice.css").read_text(encoding="utf-8")
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        self.assertIn('grid-template-rows:0fr;', practice_css.replace(" ", ""))
        self.assertIn('filterBody.classList.toggle("is-open", expanded)', shared_ui)
        self.assertIn('filterBody.style.maxHeight', shared_ui)

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
