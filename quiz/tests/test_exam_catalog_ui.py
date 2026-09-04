from pathlib import Path
import unittest


class ExamCatalogUITests(unittest.TestCase):
    def test_exam_catalog_uses_external_mobile_stylesheet_with_matching_classes(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_list.html").read_text(encoding="utf-8")
        mobile_css = (root / "static" / "css" / "pages" / "exam-mobile.css").read_text(encoding="utf-8")

        self.assertIn("exam-mobile.css", template)
        for marker in (
            ".catalog-page",
            ".catalog-grid",
            ".track-card",
            ".exam-row",
            ".individual-grid",
        ):
            self.assertIn(marker, mobile_css)

    def test_exam_catalog_does_not_depend_on_legacy_exam_list_class_names(self):
        root = Path(__file__).resolve().parents[2]
        mobile_css = (root / "static" / "css" / "pages" / "exam-mobile.css").read_text(encoding="utf-8")

        self.assertNotIn(".exam-page", mobile_css)
        self.assertNotIn(".individual-card", mobile_css)
        self.assertNotIn(".start-button", mobile_css)


if __name__ == "__main__":
    unittest.main()
