from pathlib import Path
import unittest


class AdminShellArchitectureTests(unittest.TestCase):
    def test_admin_shell_uses_shared_admin_stylesheet(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "layouts" / "admin" / "base_admin.html").read_text(encoding="utf-8")
        self.assertIn("css/admin.css", template)
        self.assertNotIn("<style>", template)
        self.assertNotIn("</style>", template)

    def test_admin_stylesheet_contains_shell_and_responsive_rules(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "admin.css").read_text(encoding="utf-8")
        for selector in (
            ".admin-header",
            ".admin-sidebar",
            ".admin-content",
            ".admin-kpi-card",
            ".admin-sidebar-overlay",
            "@media (max-width: 650px)",
        ):
            self.assertIn(selector, css)


if __name__ == "__main__":
    unittest.main()
