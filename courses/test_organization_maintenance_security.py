from django.test import TestCase

from courses.forms import CourseForm
from organizations.models import Organization
from organizations.views.admin.courses import _platform_or_organization_resource
from quiz.models import Category


class OrganizationMaintenanceSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name="Org A",
            slug="org-a-maintenance",
            org_type=Organization.TYPE_SCHOOL,
        )
        cls.other_org = Organization.objects.create(
            name="Org B",
            slug="org-b-maintenance",
            org_type=Organization.TYPE_SCHOOL,
        )
        cls.global_category = Category.objects.create(
            name="Global",
            slug="global-maintenance",
        )
        cls.own_category = Category.objects.create(
            name="Org A Category",
            slug="org-a-category-maintenance",
            organization=cls.org,
        )
        cls.foreign_category = Category.objects.create(
            name="Org B Category",
            slug="org-b-category-maintenance",
            organization=cls.other_org,
        )

    def test_course_form_restricts_categories_to_global_or_current_org(self):
        form = CourseForm(organization=self.org)
        queryset = form.fields["category"].queryset

        self.assertIn(self.global_category, queryset)
        self.assertIn(self.own_category, queryset)
        self.assertNotIn(self.foreign_category, queryset)

    def test_resource_attach_boundary_allows_global_or_current_org_only(self):
        own_resource = type("Resource", (), {"organization_id": self.org.id})()
        global_resource = type("Resource", (), {"organization_id": None})()
        foreign_resource = type("Resource", (), {"organization_id": self.other_org.id})()

        self.assertTrue(_platform_or_organization_resource(own_resource, self.org))
        self.assertTrue(_platform_or_organization_resource(global_resource, self.org))
        self.assertFalse(_platform_or_organization_resource(foreign_resource, self.org))
