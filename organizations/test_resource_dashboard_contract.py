from pathlib import Path

from django.test import SimpleTestCase

from organizations.urls import admin_patterns


class OrganizationResourceDashboardContractTests(SimpleTestCase):
    def test_exams_are_not_exposed_as_subscription_resources(self):
        route_names = {pattern.name for pattern in admin_patterns if pattern.name}

        self.assertNotIn("exam_attach", route_names)
        self.assertNotIn("exam_detach", route_names)
        self.assertIn("course_attach", route_names)
        self.assertIn("course_detach", route_names)
        self.assertIn("track_attach", route_names)
        self.assertIn("track_detach", route_names)

    def test_resource_dashboard_labels_exams_as_reusable_content(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "organizations"
            / "admin"
            / "courses"
            / "list.html"
        )
        template = template_path.read_text(encoding="utf-8")

        self.assertIn("Reusable Exams", template)
        self.assertIn("Included Exams", template)
        self.assertIn("Exams are reusable content", template)
        self.assertNotIn("exam_attach", template)
        self.assertNotIn("exam_detach", template)
