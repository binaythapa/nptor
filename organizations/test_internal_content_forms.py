from django.test import SimpleTestCase

from organizations.forms.content import OrganizationCourseForm, OrganizationExamTrackForm
from courses.forms import CourseForm
from quiz.forms import ExamTrackForm


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

    def test_platform_course_form_retains_commercial_fields(self):
        self.assertIn("subscription_plans", CourseForm.Meta.fields)
        self.assertIn("is_public", CourseForm.Meta.fields)
        self.assertIn("is_published", CourseForm.Meta.fields)

    def test_platform_track_form_retains_commercial_fields(self):
        for field in (
            "subscription_plans",
            "pricing_type",
            "monthly_price",
            "lifetime_price",
            "trial_days",
            "currency",
        ):
            self.assertIn(field, ExamTrackForm.Meta.fields)
