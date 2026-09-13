from django.test import SimpleTestCase

from organizations.views.admin.courses import OrganizationCourseForm
from organizations.views.admin.tracks import OrganizationExamTrackForm


class OrganizationInternalContentFormTests(SimpleTestCase):
    def test_organization_course_form_excludes_commercial_fields(self):
        commercial_fields = {"subscription_plans", "is_public", "is_published"}
        self.assertTrue(commercial_fields.isdisjoint(OrganizationCourseForm.Meta.fields))

    def test_organization_track_form_excludes_commercial_fields(self):
        commercial_fields = {
            "subscription_plans",
            "pricing_type",
            "monthly_price",
            "lifetime_price",
            "trial_days",
            "currency",
        }
        self.assertTrue(commercial_fields.isdisjoint(OrganizationExamTrackForm.Meta.fields))
