from types import SimpleNamespace

from django.test import SimpleTestCase

from courses.forms import CourseForm
from organizations.views.admin.courses import _platform_or_organization_resource


class OrganizationMaintenanceSecurityTests(SimpleTestCase):
    def test_course_form_restricts_categories_to_global_or_current_org(self):
        org = SimpleNamespace(id=10)
        other_org = SimpleNamespace(id=20)

        form = CourseForm(organization=org)
        queryset = form.fields["category"].queryset

        # CourseForm currently does not expose an organization-aware category
        # queryset. This regression test documents the required boundary.
        self.assertTrue(queryset.filter(organization__isnull=True).exists())
        self.assertFalse(queryset.filter(organization=other_org).exists())

    def test_resource_attach_boundary_allows_global_or_current_org_only(self):
        org = SimpleNamespace(id=10)
        own_resource = SimpleNamespace(organization_id=10)
        global_resource = SimpleNamespace(organization_id=None)
        foreign_resource = SimpleNamespace(organization_id=20)

        self.assertTrue(_platform_or_organization_resource(own_resource, org))
        self.assertTrue(_platform_or_organization_resource(global_resource, org))
        self.assertFalse(_platform_or_organization_resource(foreign_resource, org))
