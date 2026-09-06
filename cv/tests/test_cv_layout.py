from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.services.cv_builder import create_cv


class CVLayoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cv-layout", email="cv-layout@example.com", password="pass")
        self.template = CVTemplate.objects.create(name="Test", slug="layout-test", is_active=True)
        self.client.force_login(self.user)

    def test_cv_dashboard_uses_full_width_layout_without_main_sidebar(self):
        response = self.client.get(reverse("cv:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cv-route")
        self.assertContains(response, "cv-compact-ui")
        self.assertNotContains(response, 'id="site-sidebar"')

    def test_cv_dashboard_has_workspace_navigation_and_home_link(self):
        response = self.client.get(reverse("cv:dashboard"))

        self.assertContains(response, "CV Dashboard")
        self.assertContains(response, "Career Profile")
        self.assertContains(response, "Career Interview")
        self.assertContains(response, "Import CV")
        self.assertContains(response, "Create Resume")
        self.assertContains(response, "Templates")
        self.assertContains(response, f'href="{reverse("quiz:dashboard")}"')

    def test_cv_builder_uses_full_width_layout_without_main_sidebar(self):
        cv = create_cv(self.user, "Layout Test CV", self.template)

        response = self.client.get(reverse("cv:cv_builder", kwargs={"pk": cv.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cv-route")
        self.assertContains(response, "cv-compact-ui")
        self.assertNotContains(response, 'id="site-sidebar"')

    def test_cv_builder_has_cv_navigation(self):
        cv = create_cv(self.user, "Layout Test CV", self.template)

        response = self.client.get(reverse("cv:cv_builder", kwargs={"pk": cv.pk}))

        for label in ("Builder", "Preview", "AI Review", "ATS Analysis", "Tailor", "Versions", "Edit", "Duplicate", "PDF", "DOCX"):
            self.assertContains(response, label)
        self.assertContains(response, cv.title)
        self.assertContains(response, f'href="{reverse("quiz:dashboard")}"')
        self.assertContains(response, f'href="{reverse("cv:cv_preview", kwargs={"pk": cv.pk})}"')

    def test_cv_preview_is_standalone_without_website_header_or_workspace_nav(self):
        cv = create_cv(self.user, "Preview Layout Test CV", self.template)

        response = self.client.get(reverse("cv:cv_preview", kwargs={"pk": cv.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resume Preview")
        self.assertNotContains(response, "cv-workspace-nav")
        self.assertNotContains(response, "Logout")
        self.assertNotContains(response, 'class="app-layout"')
