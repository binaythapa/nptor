from pathlib import Path

from django.test import SimpleTestCase

from quiz.views.admin_subscription_views import TrackForm


class TrackFormFrontendContractTests(SimpleTestCase):
    def test_track_form_exposes_model_fields_needed_by_admin_ui(self):
        expected_fields = {
            "title",
            "slug",
            "description",
            "organization",
            "subscription_scope",
            "courses",
            "subscription_plans",
            "pricing_type",
            "monthly_price",
            "lifetime_price",
            "trial_days",
            "currency",
            "is_active",
        }

        self.assertTrue(expected_fields.issubset(TrackForm().fields.keys()))

    def test_track_template_renders_all_track_configuration_fields(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "subscription"
            / "track_form.html"
        )
        template = template_path.read_text(encoding="utf-8")

        for field_name in (
            "organization",
            "courses",
            "subscription_plans",
            "subscription_scope",
            "pricing_type",
            "monthly_price",
            "lifetime_price",
            "trial_days",
            "currency",
            "is_active",
        ):
            self.assertIn(
                f"form.{field_name}",
                template,
                msg=f"Track form template must render {field_name}.",
            )

        self.assertIn("Legacy pricing.", template)
        self.assertIn("Subscription Plans", template)


class TrackFormTemplateSyntaxTests(SimpleTestCase):
    def test_template_file_exists(self):
        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "quiz"
            / "student"
            / "subscription"
            / "track_form.html"
        )
        self.assertTrue(template_path.is_file())
