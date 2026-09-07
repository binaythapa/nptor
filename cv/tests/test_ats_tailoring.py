from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models_ai import AIConversation, ATSAnalysis, AISuggestion
from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.services.cv_ai import AIProviderError, analyze_ats, set_provider_for_tests, tailor_cv
from cv.services.cv_builder import create_cv


class FakeATSProvider:
    name = "fake"
    model = "fake-model"

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        if "score" in schema.get("properties", {}):
            return {
                "score": 78,
                "summary": "Strong data engineering alignment with a few keyword gaps.",
                "keyword_match": ["Snowflake", "Python"],
                "missing_keywords": ["Airflow"],
                "strengths": ["Data engineering experience"],
                "gaps": ["Airflow is not present"],
                "risks": ["Summary is generic"],
                "recommendations": ["Add relevant Airflow experience if truthful."],
            }
        return {
            "summary": "Tailor the existing summary toward the target role.",
            "suggestions": [
                {
                    "section": "summary",
                    "field_name": "summary",
                    "kind": "tailoring",
                    "title": "Target the summary",
                    "reason": "Emphasize existing data engineering strengths relevant to the job.",
                    "current_value": "I work with data and Snowflake.",
                    "proposed_value": "Data engineer focused on Snowflake and Python delivery.",
                }
            ],
        }


class FailingProvider:
    name = "fake-failure"
    model = "fake-model"

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        raise AIProviderError("provider unavailable")


class ATSTailoringTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ats-user", email="ats@example.com")
        self.other = get_user_model().objects.create_user(username="ats-other", email="other@example.com")
        self.template = CVTemplate.objects.create(slug="ats-template", name="ATS Template")
        self.cv = create_cv(self.user, "ATS CV", self.template)
        self.cv.profile.summary = "I work with data and Snowflake."
        self.cv.profile.save()
        self.job_description = "Senior Data Engineer. Strong Python, Snowflake and Airflow experience required."

    def tearDown(self):
        set_provider_for_tests(None)

    def test_ats_analysis_persists_score_result_job_description_and_version(self):
        set_provider_for_tests(FakeATSProvider())
        analysis = analyze_ats(self.cv, self.job_description)
        self.assertEqual(analysis.owner_id, self.user.id)
        self.assertEqual(analysis.score, 78)
        self.assertEqual(analysis.job_description, self.job_description)
        self.assertEqual(analysis.result["missing_keywords"], ["Airflow"])
        self.assertIsNotNone(analysis.cv_version_id)
        self.assertEqual(analysis.conversation.purpose, AIConversation.PURPOSE_JOB_MATCH)

    def test_ats_analysis_rejects_cv_owned_by_another_user(self):
        set_provider_for_tests(FakeATSProvider())
        self.cv.owner = self.other
        self.cv.save(update_fields=["owner"])
        with self.assertRaises(ValueError):
            analyze_ats(self.cv, self.job_description)
        self.assertEqual(ATSAnalysis.objects.count(), 0)

    def test_ats_provider_failure_is_explicit(self):
        set_provider_for_tests(FailingProvider())
        with self.assertRaises(AIProviderError):
            analyze_ats(self.cv, self.job_description)
        self.assertEqual(ATSAnalysis.objects.count(), 0)

    def test_tailoring_creates_pending_suggestions_without_master_profile_change(self):
        set_provider_for_tests(FakeATSProvider())
        conversation = tailor_cv(self.cv, self.job_description)
        suggestion = conversation.suggestions.get()
        self.assertEqual(conversation.purpose, AIConversation.PURPOSE_JOB_MATCH)
        self.assertEqual(suggestion.status, AISuggestion.STATUS_PENDING)
        self.cv.profile.refresh_from_db()
        self.assertEqual(self.cv.profile.summary, "I work with data and Snowflake.")

    def test_accept_tailoring_updates_cv_override_only(self):
        set_provider_for_tests(FakeATSProvider())
        conversation = tailor_cv(self.cv, self.job_description)
        suggestion = conversation.suggestions.get()
        self.client.force_login(self.user)
        response = self.client.post(reverse("cv:cv_ai_suggestion_accept", kwargs={"pk": suggestion.pk}))
        self.assertRedirects(response, reverse("cv:cv_ai_tailor", kwargs={"pk": self.cv.pk}))
        self.cv.refresh_from_db()
        self.cv.profile.refresh_from_db()
        self.assertEqual(self.cv.overrides["summary"], "Data engineer focused on Snowflake and Python delivery.")
        self.assertEqual(self.cv.profile.summary, "I work with data and Snowflake.")

    def test_ats_page_requires_login_and_ownership(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_ats_analysis", kwargs={"pk": self.cv.pk}))
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.other)
        response = self.client.get(reverse("cv:cv_ats_analysis", kwargs={"pk": self.cv.pk}))
        self.assertEqual(response.status_code, 404)

    def test_tailor_page_requires_job_description_before_provider_call(self):
        set_provider_for_tests(FakeATSProvider())
        self.client.force_login(self.user)
        response = self.client.post(reverse("cv:cv_ai_tailor", kwargs={"pk": self.cv.pk}), {"job_description": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Job description is required")
        self.assertEqual(AIConversation.objects.count(), 0)
