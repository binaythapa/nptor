from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import ATSAnalysis, AIConversation, CareerProfile, CVTemplate
from cv.models_cv import CV
from cv.services.ai.career_interviewer import interview_turn
from cv.services.ai.cv_reviewer import review_cv
from cv.services.ai.cv_writer import rewrite_bullet, suggest_summary
from cv.services.ai.job_matcher import match_job
from cv.services.cv_ai import (
    analyze_ats as legacy_analyze_ats,
    review_cv as legacy_review_cv,
    set_provider_for_tests,
    tailor_cv as legacy_tailor_cv,
)
from cv.services.cv_builder import create_cv_version


class FakeProvider:
    name = "fake"
    model = "test-model"

    def generate_text(self, prompt, *, system_prompt="", model=None):
        return "A concise professional summary."

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        if "reply" in schema["properties"]:
            return {
                "reply": "Tell me about a project you are proud of.",
                "facts": [{
                    "section": "experience",
                    "field_name": "job_title",
                    "proposed_value": "Software Engineer",
                    "confirmed": False,
                    "evidence": "User stated this in the conversation.",
                }],
                "next_question": "What did you build?",
            }
        if "score" in schema["properties"] and "strengths" in schema["properties"]:
            return {"score": 84, "strengths": ["clear structure"], "gaps": ["metrics"], "suggestions": ["add measurable outcomes"]}
        return {"match_score": 76, "matching_skills": ["Python"], "missing_skills": ["Kubernetes"], "recommendations": ["Highlight relevant projects"]}


class AIServicesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ai-service", email="ai-service@example.com", password="pass")
        self.profile = CareerProfile.objects.create(user=self.user)
        self.template = CVTemplate.objects.create(name="Test", slug="test", is_active=True)
        self.cv = CV.objects.create(owner=self.user, profile=self.profile, template=self.template, title="My CV")
        self.version = create_cv_version(self.cv)
        self.provider = FakeProvider()
        set_provider_for_tests(self.provider)

    def tearDown(self):
        set_provider_for_tests(None)

    def test_writer_returns_unconfirmed_suggestion(self):
        result = suggest_summary({"professional_title": "Engineer"}, provider=self.provider)
        self.assertFalse(result["confirmed"])

    def test_rewrite_returns_unconfirmed_suggestion(self):
        result = rewrite_bullet("Built reports", {"role": "Engineer"}, provider=self.provider)
        self.assertFalse(result["confirmed"])

    def test_reviewer_creates_analysis_for_version_owner(self):
        analysis = review_cv(self.version, provider=self.provider)
        self.assertEqual(analysis.owner_id, self.user.id)
        self.assertEqual(analysis.cv_version_id, self.version.id)
        self.assertEqual(analysis.score, 84)

    def test_interviewer_stores_proposed_facts_unconfirmed(self):
        conversation = AIConversation.objects.create(owner=self.user, cv=self.cv)
        result = interview_turn(conversation, "I am a Software Engineer.", provider=self.provider)
        self.assertEqual(len(result["extractions"]), 1)
        self.assertFalse(result["extractions"][0].confirmed)

    def test_job_match_is_suggestion_only(self):
        result = match_job({"skills": ["Python"]}, "Need Python and Kubernetes", provider=self.provider)
        self.assertEqual(result["match_score"], 76)
        self.assertFalse(result["confirmed"])

    def test_legacy_review_uses_shared_provider_factory(self):
        conversation = legacy_review_cv(self.cv)
        self.assertEqual(conversation.provider, "fake")
        self.assertEqual(conversation.model, "test-model")
        self.assertEqual(conversation.suggestions.count(), 1)

    def test_legacy_ats_uses_shared_provider_factory(self):
        analysis = legacy_analyze_ats(self.cv, "Need Python and Kubernetes")
        self.assertEqual(analysis.provider, "fake")
        self.assertEqual(analysis.score, 76)

    def test_legacy_tailoring_uses_shared_provider_factory(self):
        conversation = legacy_tailor_cv(self.cv, "Need Python and Kubernetes")
        self.assertEqual(conversation.provider, "fake")
        self.assertEqual(conversation.metadata["analysis"], "tailoring")
        self.assertEqual(conversation.suggestions.count(), 1)
