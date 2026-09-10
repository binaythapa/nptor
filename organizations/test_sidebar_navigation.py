from django.template.loader import get_template
from django.test import SimpleTestCase
from django.test.client import RequestFactory


class OrganizationSidebarNavigationTests(SimpleTestCase):
    def setUp(self):
        self.template = get_template("layouts/student/sidebar.html")
        self.factory = RequestFactory()

    def render_sidebar(self, *, can_manage_organization):
        request = self.factory.get("/")
        request.active_org = type("OrganizationStub", (), {"slug": "demo-org"})()
        request.can_manage_organization = can_manage_organization
        request.user = type("UserStub", (), {"is_authenticated": True})()
        return self.template.render({"request": request, "user": request.user, "is_from_course": False})

    def test_staff_or_teacher_gets_member_organization_link(self):
        content = self.render_sidebar(can_manage_organization=False)

        self.assertIn('href="/organizations/demo-org/"', content)
        self.assertIn("Organization", content)
        self.assertIn("View", content)
        self.assertNotIn('href="/organizations/admin/demo-org/dashboard/"', content)

    def test_organization_admin_gets_management_link(self):
        content = self.render_sidebar(can_manage_organization=True)

        self.assertIn('href="/organizations/admin/demo-org/dashboard/"', content)
        self.assertIn("Organization", content)
        self.assertIn("Manage", content)
