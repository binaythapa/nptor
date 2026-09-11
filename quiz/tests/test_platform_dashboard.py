from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PlatformDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin", password="test-password", is_superuser=True, is_staff=True)
        self.staff = User.objects.create_user(username="staff", password="test-password", is_staff=True)

    def test_platform_admin_can_view_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("quiz:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Platform overview")
        self.assertContains(response, "Needs attention")

    def test_non_platform_user_is_denied(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("quiz:admin_dashboard"))
        self.assertEqual(response.status_code, 403)
