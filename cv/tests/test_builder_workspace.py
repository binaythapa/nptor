import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import CareerProfile, CVTemplate
from cv.models_cv import CV
from cv.services.cv_ai import set_provider_for_tests
from cv.tests.test_ai_services import FakeProvider


class BuilderWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="builder", email="builder@example.com", password="pass")
        self.other = get_user_model().objects.create_user(username="other", email="other@example.com", password="pass")
        self.profile = CareerProfile.objects.create(user=self.user)
        self.template = CVTemplate.objects.create(name="Test", slug="builder-test", is_active=True)
        self.cv = CV.objects.create(owner=self.user, profile=self.profile, template=self.template, title="Target CV")

    def tearDown(self):
        set_provider_for_tests(None)

    def test_autosave_persists_target_job_and_profile_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cv:cv_builder_autosave", args=[self.cv.pk]),
            data=json.dumps({
                "title": "Data Engineer - ACME",
                "professional_title": "Data Engineer",
                "summary": "Snowflake and Python engineer",
                "target_job": {
                    "title": "Senior Data Engineer",
                    "company": "ACME",
                    "description": "Snowflake Python AWS",
                },
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.cv.refresh_from_db()
        self.assertEqual(self.cv.overrides["target_job"]["company"], "ACME")
        self.assertEqual(self.cv.overrides["summary"], "Snowflake and Python engineer")

    def test_autosave_cannot_modify_another_users_cv(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("cv:cv_builder_autosave", args=[self.cv.pk]),
            data=json.dumps({"title": "Hacked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_ai_summary_endpoint_returns_unconfirmed_suggestion(self):
        self.client.force_login(self.user)
        set_provider_for_tests(FakeProvider())
        response = self.client.post(
            reverse("cv:cv_builder_ai", args=[self.cv.pk]),
            data=json.dumps({"action": "summary"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["suggestion"]["confirmed"])

    def test_ats_endpoint_uses_target_job_description(self):
        self.client.force_login(self.user)
        set_provider_for_tests(FakeProvider())
        response = self.client.post(
            reverse("cv:cv_builder_ats", args=[self.cv.pk]),
            data=json.dumps({"job_description": "Need Python and Kubernetes"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"]["score"], 76)

    def test_builder_renders_workspace_panels(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_builder", args=[self.cv.pk]))
        self.assertContains(response, 'data-builder-workspace="true"')
        self.assertContains(response, 'id="cv-preview-frame"')
        self.assertContains(response, "Target job")
