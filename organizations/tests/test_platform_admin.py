from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from organizations.models.membership import OrganizationMember
from organizations.models.organization import Organization
from organizations.models.role import OrganizationRole
from organizations.permissions import platform_admin_required


class PlatformAdminAuthorizationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="platform", password="test-password", is_staff=True, is_superuser=True)
        self.teacher = User.objects.create_user(username="teacher", password="test-password", is_staff=True)
        self.student = User.objects.create_user(username="student", password="test-password")
        self.organization = Organization.objects.create(name="School", slug="school", created_by=self.admin)
        OrganizationMember.objects.create(user=self.teacher, organization=self.organization, role=OrganizationRole.STAFF)
        self.factory = RequestFactory()

    def _view(self, request):
        return "ok"

    def test_superuser_is_platform_admin(self):
        request = self.factory.get("/")
        request.user = self.admin
        self.assertEqual(platform_admin_required(self._view)(request), "ok")

    def test_organization_staff_is_not_platform_admin(self):
        request = self.factory.get("/")
        request.user = self.teacher
        with self.assertRaises(PermissionDenied):
            platform_admin_required(self._view)(request)

    def test_student_is_not_platform_admin(self):
        request = self.factory.get("/")
        request.user = self.student
        with self.assertRaises(PermissionDenied):
            platform_admin_required(self._view)(request)
