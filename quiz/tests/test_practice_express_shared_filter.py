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

    def test_express_filter_clears_body_padding_when_collapsed(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        start = shared_ui.index("function initExpressFilterCollapseCompatibility()")
        end = shared_ui.index("initExpressFilterCollapseCompatibility();", start)
        filter_code = shared_ui[start:end]

        self.assertIn('body.style.padding = expanded ? "4px 15px 15px" : "0"', filter_code)
        self.assertIn('new MutationObserver(syncFilterPadding)', filter_code)
        self.assertIn('attributeFilter: ["style"]', filter_code)


if __name__ == "__main__":
    unittest.main()
