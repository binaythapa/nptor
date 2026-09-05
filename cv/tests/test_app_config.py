from django.apps import apps
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class CVAppConfigTests(SimpleTestCase):
    def test_cv_app_is_installed(self):
        self.assertEqual(apps.get_app_config("cv").name, "cv")

    def test_cv_workspace_route_exists(self):
        self.assertEqual(reverse("cv:dashboard"), "/cv/")
        self.assertEqual(resolve("/cv/").url_name, "dashboard")
