from django.template.loader import render_to_string
from django.test import SimpleTestCase


class CourseBuilderNavigationTemplateTests(SimpleTestCase):
    template_name = "courses/base.html"

    def render(self, **context):
        request = context.pop("request", None)
        if request is None:
            request = type("Request", (), {})()
        context["request"] = request
        context.setdefault("user", type("User", (), {"is_authenticated": True})())
        return render_to_string(self.template_name, context=context, request=request)

    def test_platform_admin_gets_nptor_admin_dashboard(self):
        user = type("User", (), {"is_authenticated": True, "is_staff": True, "is_superuser": True})()
        html = self.render(user=user, request=type("Request", (), {"organization": None, "active_org": None})())
        self.assertIn("{%", "") if False else None
        self.assertIn('/quiz/dashboard/admin/', html)
        self.assertIn('Back to Dashboard', html)

    def test_normal_user_gets_student_dashboard(self):
        user = type("User", (), {"is_authenticated": True, "is_staff": False, "is_superuser": False})()
        html = self.render(user=user, request=type("Request", (), {"organization": None, "active_org": None})())
        self.assertIn('/quiz/dashboard/student/', html)
        self.assertIn('Back to Dashboard', html)

    def test_organization_administrator_gets_org_dashboard(self):
        org = type("Org", (), {"slug": "acme"})()
        member = type("Member", (), {"is_administrator": True})()
        request = type("Request", (), {"organization": org, "organization_member": member, "active_org": org})()
        html = self.render(request=request)
        self.assertIn('/organizations/acme/admin/', html)
        self.assertIn('Back to Dashboard', html)

    def test_organization_staff_gets_org_workspace(self):
        org = type("Org", (), {"slug": "acme"})()
        member = type("Member", (), {"is_administrator": False})()
        request = type("Request", (), {"organization": org, "organization_member": member, "active_org": org})()
        html = self.render(request=request)
        self.assertIn('/organizations/acme/workspace/', html)
        self.assertIn('Back to Dashboard', html)
