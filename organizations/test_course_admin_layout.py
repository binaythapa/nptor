from pathlib import Path

from django.test import SimpleTestCase


class OrganizationCourseAdminLayoutTests(SimpleTestCase):
    def test_organization_course_create_template_uses_organization_admin_shell(self):
        template_path = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "organizations"
            / "admin"
            / "courses"
            / "create.html"
        )

        source = template_path.read_text(encoding="utf-8")
        self.assertTrue(
            source.startswith('{% extends "organizations/admin/base.html" %}'),
            "Organization course creation must use the shared organization admin shell.",
        )
        self.assertNotIn(
            '{% extends "courses/base.html" %}',
            source,
        )
