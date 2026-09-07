from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from organizations.middleware import ActiveOrganizationMiddleware
from organizations.models import Organization, OrganizationMember, OrganizationRole


User = get_user_model()


class OrganizationSidebarTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Sidebar School",
            slug="sidebar-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        self.owner = User.objects.create_user(username="sidebar-owner", password="password")
        self.admin = User.objects.create_user(username="sidebar-admin", password="password")
        self.staff = User.objects.create_user(username="sidebar-staff", password="password")
        self.student = User.objects.create_user(username="sidebar-student", password="password")
        OrganizationMember.objects.create(
            user=self.owner, organization=self.organization, role=OrganizationRole.ORG_OWNER
        )
        OrganizationMember.objects.create(
            user=self.admin, organization=self.organization, role=OrganizationRole.ORG_ADMIN
        )
        OrganizationMember.objects.create(
            user=self.staff, organization=self.organization, role=OrganizationRole.STAFF
        )
        OrganizationMember.objects.create(
            user=self.student, organization=self.organization, role=OrganizationRole.STUDENT
        )
        self.factory = RequestFactory()

    def render_sidebar(self, user):
        request = self.factory.get("/quiz/dashboard/student/")
        request.user = user
        ActiveOrganizationMiddleware(lambda request: request)(request)
        return render_to_string(
            "layouts/student/sidebar.html",
            {"user": user, "is_from_course": False},
            request=request,
        )

    def test_owner_sees_organization_dashboard_link(self):
        html = self.render_sidebar(self.owner)
        self.assertIn("Organization", html)
        self.assertIn("Org Dashboard", html)
        self.assertIn("/org/sidebar-school/admin/dashboard/", html)

    def test_admin_sees_organization_dashboard_link(self):
        html = self.render_sidebar(self.admin)
        self.assertIn("Organization", html)
        self.assertIn("Org Dashboard", html)
        self.assertIn("/org/sidebar-school/admin/dashboard/", html)

    def test_staff_does_not_see_organization_dashboard_link(self):
        html = self.render_sidebar(self.staff)
        self.assertNotIn("Org Dashboard", html)

    def test_student_does_not_see_organization_dashboard_link(self):
        html = self.render_sidebar(self.student)
        self.assertNotIn("Org Dashboard", html)

    def test_owner_membership_is_preferred_when_user_has_multiple_organizations(self):
        other_org = Organization.objects.create(
            name="Other Sidebar School",
            slug="other-sidebar-school",
            org_type=Organization.TYPE_SCHOOL,
            is_active=True,
        )
        OrganizationMember.objects.create(
            user=self.owner, organization=other_org, role=OrganizationRole.STUDENT
        )

        request = self.factory.get("/quiz/dashboard/student/")
        request.user = self.owner
        ActiveOrganizationMiddleware(lambda request: request)(request)

        self.assertEqual(request.active_org, self.organization)
        self.assertEqual(request.org_role, OrganizationRole.ORG_OWNER)
        self.assertTrue(request.can_manage_organization)
