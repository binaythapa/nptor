from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import AIConversation, AIExtraction, CareerProfile
from cv.services.ai.career_interviewer import interview_turn


class FakeInterviewProvider:
    name = "fake"
    model = "test-model"

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        return {
            "reply": "What was your biggest achievement in that role?",
            "facts": [
                {
                    "section": "experience",
                    "field_name": "job_title",
                    "proposed_value": "Data Engineer",
                    "confirmed": False,
                    "evidence": "The user stated this in the conversation.",
                }
            ],
            "next_question": "What was your biggest achievement in that role?",
        }


class CareerProfileInterviewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="career-user", password="password")
        self.other_user = user_model.objects.create_user(username="career-other", password="password")
        self.client.force_login(self.user)

    def test_profile_page_exposes_all_three_profile_entry_points(self):
        response = self.client.get(reverse("cv:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("cv:cv_import"))
        self.assertContains(response, reverse("cv:career_interview"))
        self.assertContains(response, "Edit manually")

    def test_interview_turn_persists_unconfirmed_extraction(self):
        conversation = AIConversation.objects.create(owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW)
        result = interview_turn(conversation, "I am a Data Engineer.", provider=FakeInterviewProvider())
        extraction = result["extractions"][0]
        self.assertFalse(extraction.confirmed)
        self.assertEqual(extraction.conversation.owner_id, self.user.id)

    def test_confirm_interview_extraction_records_user_and_value(self):
        conversation = AIConversation.objects.create(owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW)
        extraction = AIExtraction.objects.create(
            conversation=conversation,
            section="experience",
            field_name="job_title",
            proposed_value="Data Engineer",
        )
        response = self.client.post(
            reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}),
            {"value": "Senior Data Engineer"},
        )
        self.assertRedirects(response, reverse("cv:career_interview"))
        extraction.refresh_from_db()
        self.assertTrue(extraction.confirmed)
        self.assertEqual(extraction.proposed_value, "Senior Data Engineer")
        self.assertEqual(extraction.confirmed_by_id, self.user.id)
        self.assertIsNotNone(extraction.confirmed_at)

    def test_other_user_cannot_confirm_interview_extraction(self):
        conversation = AIConversation.objects.create(owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW)
        extraction = AIExtraction.objects.create(
            conversation=conversation,
            section="experience",
            field_name="job_title",
            proposed_value="Data Engineer",
        )
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}),
            {"value": "Changed"},
        )
        self.assertEqual(response.status_code, 404)
        extraction.refresh_from_db()
        self.assertFalse(extraction.confirmed)

    def test_interview_page_is_owner_scoped(self):
        conversation = AIConversation.objects.create(owner=self.other_user, purpose=AIConversation.PURPOSE_INTERVIEW)
        response = self.client.get(reverse("cv:career_interview", kwargs={"conversation_id": conversation.pk}))
        self.assertEqual(response.status_code, 404)

    def test_profile_is_created_for_interview_entry_point(self):
        self.assertFalse(CareerProfile.objects.filter(user=self.user).exists())
        response = self.client.get(reverse("cv:career_interview"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CareerProfile.objects.filter(user=self.user).exists())
