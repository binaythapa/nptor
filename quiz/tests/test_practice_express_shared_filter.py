from pathlib import Path
import unittest


class PracticeExpressSharedFilterTests(unittest.TestCase):
    def test_express_loads_the_shared_practice_stylesheet(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        start = shared_ui.index("function initExpressFilterLayout()")
        end = shared_ui.index("initExpressFilterLayout();", start)
        filter_code = shared_ui[start:end]

        self.assertIn("/css/pages/practice.css", filter_code)
        self.assertIn('rel = "stylesheet"', filter_code)
        self.assertIn('data-practice-shared-styles', filter_code)

    def test_express_filter_does_not_keep_legacy_filter_class_after_shared_mapping(self):
        root = Path(__file__).resolve().parents[2]
        shared_ui = (root / "static" / "js" / "ui.js").read_text(encoding="utf-8")

        start = shared_ui.index("function initExpressFilterLayout()")
        end = shared_ui.index("initExpressFilterLayout();", start)
        filter_code = shared_ui[start:end]

        self.assertIn("practice-express-filter", filter_code)
        self.assertIn("classList.remove(\"practice-express-filter\", \"box\", \"mb-3\", \"p-3\")", filter_code)
        self.assertIn('classList.add("practice-filter-body")', filter_code)
        self.assertIn('classList.add("practice-filter-form")', filter_code)
        self.assertIn('classList.toggle("is-open"', filter_code)


if __name__ == "__main__":
    unittest.main()
