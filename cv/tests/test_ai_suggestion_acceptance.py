from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import AIConversation, AISuggestion, CareerExperience, CareerProfile, CVTemplate
from cv.models_cv import CV
from cv.services.cv_ai import accept_suggestion


class AISuggestionAcceptanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ai-accept", email="ai-accept@example.com", password="pass")
        self.profile = CareerProfile.objects.create(user=self.user)
        self.template = CVTemplate.objects.create(name="Test", slug="acceptance-test", is_active=True)
        self.cv = CV.objects.create(owner=self.user, profile=self.profile, template=self.template, title="My CV")

    def test_accept_experience_job_title_updates_profile_record(self):
        experience = CareerExperience.objects.create(profile=self.profile, job_title="Seniour Architect ENgneer", employer="Example Ltd")
        conversation = AIConversation.objects.create(owner=self.user, cv=self.cv, purpose=AIConversation.PURPOSE_REVIEW)
        suggestion = AISuggestion.objects.create(conversation=conversation, section="experiences", field_name="job_title", title="Fix spelling in job title", current_value="Seniour Architect ENgneer", proposed_value="Senior Architect Engineer")

        accepted = accept_suggestion(suggestion, self.user)

        experience.refresh_from_db()
        self.assertEqual(accepted.status, AISuggestion.STATUS_ACCEPTED)
        self.assertEqual(experience.job_title, "Senior Architect Engineer")

    def test_accept_experience_job_title_view_updates_profile_record(self):
        experience = CareerExperience.objects.create(profile=self.profile, job_title="Seniour Architect ENgneer", employer="Example Ltd")
        conversation = AIConversation.objects.create(owner=self.user, cv=self.cv, purpose=AIConversation.PURPOSE_REVIEW)
        suggestion = AISuggestion.objects.create(conversation=conversation, section="experiences", field_name="job_title", title="Fix spelling in job title", current_value="Seniour Architect ENgneer", proposed_value="Senior Architect Engineer")
        self.client.force_login(self.user)

        response = self.client.post(reverse("cv:cv_ai_suggestion_accept", kwargs={"pk": suggestion.pk}))

        experience.refresh_from_db()
        suggestion.refresh_from_db()
        self.assertRedirects(response, reverse("cv:cv_ai_review", kwargs={"pk": self.cv.pk}))
        self.assertEqual(experience.job_title, "Senior Architect Engineer")
        self.assertEqual(suggestion.status, AISuggestion.STATUS_ACCEPTED)
