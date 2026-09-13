from pathlib import Path

from django.test import SimpleTestCase


class OrganizationCourseAdminLayoutTests(SimpleTestCase):
    def _assert_organization_admin_shell(self, relative_path):
        template_path = Path(__file__).resolve().parent.parent / "templates" / relative_path
        source = template_path.read_text(encoding="utf-8")
        self.assertTrue(
            source.startswith('{% extends "organizations/admin/base.html" %}'),
            "Organization course pages must use the shared organization admin shell.",
        )
        self.assertNotIn(
            '{% extends "courses/base.html" %}',
            source,
        )

    def test_organization_course_create_template_uses_organization_admin_shell(self):
        self._assert_organization_admin_shell(
            "organizations/admin/courses/create.html",
        )

    def test_organization_course_edit_template_uses_organization_admin_shell(self):
        self._assert_organization_admin_shell(
            "organizations/admin/courses/edit.html",
        )
