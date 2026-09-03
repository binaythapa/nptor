from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.template.loader import get_template


class ResponsiveQATemplateTests(SimpleTestCase):
    def test_student_shell_has_mobile_viewport_and_responsive_layer(self):
        template = get_template("layouts/student/base.html")
        source = template.template.source

        self.assertIn('name="viewport"', source)
        self.assertIn("static 'css/responsive.css'", source)

    def test_student_navigation_uses_shared_mobile_breakpoint_contract(self):
        navigation_path = Path(settings.BASE_DIR) / "static" / "js" / "navigation.js"
        source = navigation_path.read_text(encoding="utf-8")

        self.assertIn("const MOBILE_BREAKPOINT = 1023;", source)

    def test_org_admin_shell_has_mobile_navigation_and_responsive_css(self):
        template = get_template("organizations/admin/base.html")
        source = template.template.source

        self.assertIn('name="viewport"', source)
        self.assertIn("org-admin-mobile.css", source)
        self.assertIn('id="orgMobileMenuButton"', source)
        self.assertIn('id="orgAdminSidebar"', source)
        self.assertIn('id="orgAdminBackdrop"', source)
