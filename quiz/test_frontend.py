from pathlib import Path

from django.test import SimpleTestCase


class FrontendAccessibilityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[1]

    def test_student_layout_has_skip_link_and_main_landmark(self):
        template = (self.root / "templates/layouts/student/base.html").read_text()
        self.assertIn('href="#main-content"', template)
        self.assertIn('id="main-content"', template)

    def test_admin_navigation_has_accessible_mobile_toggle(self):
        header = (self.root / "templates/layouts/admin/header_admin.html").read_text()
        script = (self.root / "static/js/admin_navigation.js").read_text()
        self.assertIn('id="admin-sidebar-toggle"', header)
        self.assertIn('aria-controls="admin-sidebar"', header)
        self.assertIn('admin-sidebar-toggle', script)
        self.assertIn('Escape', script)

    def test_responsive_styles_honor_reduced_motion(self):
        css = (self.root / "static/css/responsive.css").read_text()
        self.assertIn("prefers-reduced-motion: reduce", css)
