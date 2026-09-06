from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import CareerExperience
from cv.models_ai import AIConversation, AISuggestion
from cv.models_cv import CV
from cv.models_template import CVTemplate
from cv.services.cv_ai import AIProviderError, review_cv, set_provider_for_tests
from cv.services.cv_builder import create_cv


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def review(self, payload):
        return {
            "summary": "The summary is too generic.",
            "suggestions": [
                {
                    "section": "summary",
                    "field_name": "summary",
                    "kind": "rewrite",
                    "title": "Strengthen the summary",
                    "reason": "Lead with measurable outcomes and domain expertise.",
                    "current_value": payload.get("summary", ""),
                    "proposed_value": "Senior data engineer with measurable cloud delivery impact.",
                }
            ],
        }


class FailingProvider:
    name = "fake-failure"
    model = "fake-model"

    def review(self, payload):
        raise AIProviderError("provider unavailable")


class CVAIWriterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ai-user", email="ai@example.com")
        self.other = get_user_model().objects.create_user(username="ai-other", email="other@example.com")
        self.template = CVTemplate.objects.create(slug="ai-template", name="AI Template")
        self.cv = create_cv(self.user, "AI CV", self.template)
        self.cv.profile.summary = "I work with data."
        self.cv.profile.save()
        CareerExperience.objects.create(profile=self.cv.profile, job_title="Data Engineer", employer="Example")

    def test_review_creates_conversation_and_pending_suggestion_without_overwriting_profile(self):
        set_provider_for_tests(FakeProvider())
        result = review_cv(self.cv)
        self.assertEqual(result.conversation.purpose, AIConversation.PURPOSE_REVIEW)
        suggestion = result.conversation.suggestions.get()
        self.assertFalse(suggestion.accepted)
        self.assertEqual(suggestion.status, AISuggestion.STATUS_PENDING)
        self.cv.profile.refresh_from_db()
        self.assertEqual(self.cv.profile.summary, "I work with data.")

    def test_review_is_scoped_to_cv_owner(self):
        set_provider_for_tests(FakeProvider())
        self.cv.owner = self.other
        self.cv.save(update_fields=["owner"])
        with self.assertRaises(ValueError):
            review_cv(self.cv)

    def test_review_provider_failure_is_explicit(self):
        set_provider_for_tests(FailingProvider())
        with self.assertRaises(AIProviderError):
            review_cv(self.cv)

    def test_review_page_requires_login_and_ownership(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("cv:cv_ai_review", kwargs={"pk": self.cv.pk}))
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.other)
        response = self.client.get(reverse("cv:cv_ai_review", kwargs={"pk": self.cv.pk}))
        self.assertEqual(response.status_code, 404)

    def test_accept_suggestion_updates_cv_override_not_master_profile(self):
        set_provider_for_tests(FakeProvider())
        result = review_cv(self.cv)
        suggestion = result.conversation.suggestions.get()
        self.client.force_login(self.user)
        response = self.client.post(reverse("cv:cv_ai_suggestion_accept", kwargs={"pk": suggestion.pk}))
        self.assertRedirects(response, reverse("cv:cv_ai_review", kwargs={"pk": self.cv.pk}))
        suggestion.refresh_from_db()
        self.cv.refresh_from_db()
        self.cv.profile.refresh_from_db()
        self.assertTrue(suggestion.accepted)
        self.assertEqual(suggestion.status, AISuggestion.STATUS_ACCEPTED)
        self.assertEqual(self.cv.overrides["summary"], "Senior data engineer with measurable cloud delivery impact.")
        self.assertEqual(self.cv.profile.summary, "I work with data.")

    def test_reject_suggestion_does_not_change_cv(self):
        set_provider_for_tests(FakeProvider())
        result = review_cv(self.cv)
        suggestion = result.conversation.suggestions.get()
        self.client.force_login(self.user)
        self.client.post(reverse("cv:cv_ai_suggestion_reject", kwargs={"pk": suggestion.pk}))
        suggestion.refresh_from_db()
        self.cv.refresh_from_db()
        self.assertEqual(suggestion.status, AISuggestion.STATUS_REJECTED)
        self.assertNotIn("summary", self.cv.overrides)
