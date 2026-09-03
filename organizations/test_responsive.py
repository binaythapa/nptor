from pathlib import Path

from django.test import SimpleTestCase
from django.template.loader import get_template


class OrganizationAdminResponsiveTemplateTests(SimpleTestCase):
    def test_admin_base_contains_mobile_navigation_hooks(self):
        template = get_template("organizations/admin/base.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn('class="org-mobile-menu-btn"', source)
        self.assertIn('id="orgAdminSidebar"', source)
        self.assertIn('id="orgAdminBackdrop"', source)
        self.assertIn("org-admin-mobile.css", source)
        self.assertIn("class=\"org-admin-content\"", source)

    def test_dashboard_has_responsive_content_wrapper(self):
        template = get_template("organizations/admin/dashboard.html")
        source = Path(template.origin.name).read_text(encoding="utf-8")

        self.assertIn('class="org-dashboard"', source)
        self.assertIn('class="org-stat-grid"', source)
