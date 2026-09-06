from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cv.models import (
    AIConversation,
    AIExtraction,
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerProfile,
    CareerProject,
    CareerSkill,
)
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
        self.conversation = AIConversation.objects.create(owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW)

    def confirm(self, section, field_name, value):
        extraction = AIExtraction.objects.create(
            conversation=self.conversation,
            section=section,
            field_name=field_name,
            proposed_value=value,
        )
        response = self.client.post(
            reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}),
            {"value": value},
        )
        self.assertEqual(response.status_code, 302)
        return extraction

    def test_profile_page_exposes_all_three_profile_entry_points(self):
        response = self.client.get(reverse("cv:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("cv:cv_import"))
        self.assertContains(response, reverse("cv:career_interview"))
        self.assertContains(response, "Edit manually")

    def test_interview_turn_persists_unconfirmed_extraction(self):
        result = interview_turn(self.conversation, "I am a Data Engineer.", provider=FakeInterviewProvider())
        extraction = result["extractions"][0]
        self.assertFalse(extraction.confirmed)
        self.assertEqual(extraction.conversation.owner_id, self.user.id)

    def test_confirm_interview_extraction_records_user_and_value(self):
        extraction = AIExtraction.objects.create(
            conversation=self.conversation,
            section="experience",
            field_name="job_title",
            proposed_value="Data Engineer",
        )
        response = self.client.post(
            reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}),
            {"value": "Senior Data Engineer"},
        )
        self.assertRedirects(response, reverse("cv:career_interview", kwargs={"conversation_id": self.conversation.pk}))
        extraction.refresh_from_db()
        self.assertTrue(extraction.confirmed)
        self.assertEqual(extraction.proposed_value, "Senior Data Engineer")
        self.assertEqual(extraction.confirmed_by_id, self.user.id)
        self.assertIsNotNone(extraction.confirmed_at)

    def test_confirmed_experience_facts_materialize_profile_record(self):
        self.confirm("experience", "job_title", "Data Engineer")
        self.assertFalse(CareerProfile.objects.get(user=self.user).careerexperience_records.exists())
        self.confirm("experience", "employer", "Acme")
        self.confirm("experience", "description", "Built ETL pipelines")
        record = CareerProfile.objects.get(user=self.user).careerexperience_records.get()
        self.assertEqual(record.job_title, "Data Engineer")
        self.assertEqual(record.employer, "Acme")
        self.assertEqual(record.description, "Built ETL pipelines")
        self.assertEqual(record.source, "ai_interview")
        self.assertTrue(record.is_confirmed)

    def test_confirmed_education_materializes_record(self):
        self.confirm("education", "qualification", "B.Tech")
        self.confirm("education", "institution", "ABC University")
        self.confirm("education", "field_of_study", "Computer Science")
        record = CareerProfile.objects.get(user=self.user).careereducation_records.get()
        self.assertEqual(record.qualification, "B.Tech")
        self.assertEqual(record.institution, "ABC University")
        self.assertEqual(record.field_of_study, "Computer Science")

    def test_confirmed_project_materializes_once(self):
        self.confirm("projects", "name", "Data Platform")
        self.confirm("projects", "description", "Built a cloud data platform")
        self.confirm("projects", "name", "Data Platform")
        records = CareerProfile.objects.get(user=self.user).careerproject_records.filter(name="Data Platform")
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.get().description, "Built a cloud data platform")

    def test_confirmed_skill_materializes_once(self):
        self.confirm("skills", "name", "Python")
        self.confirm("skills", "category", "Programming")
        self.assertEqual(CareerProfile.objects.get(user=self.user).careerskill_records.filter(name="Python").count(), 1)
        self.assertEqual(CareerProfile.objects.get(user=self.user).careerskill_records.get().category, "Programming")

    def test_confirmed_achievement_materializes_record(self):
        self.confirm("achievements", "title", "Performance Award")
        self.confirm("achievements", "description", "Recognized for improving reliability")
        record = CareerProfile.objects.get(user=self.user).careerachievement_records.get()
        self.assertEqual(record.title, "Performance Award")
        self.assertEqual(record.description, "Recognized for improving reliability")

    def test_confirmed_certification_materializes_record(self):
        self.confirm("certifications", "name", "SnowPro Core")
        self.confirm("certifications", "issuer", "Snowflake")
        self.confirm("certifications", "credential_id", "ABC123")
        record = CareerProfile.objects.get(user=self.user).careercertification_records.get()
        self.assertEqual(record.name, "SnowPro Core")
        self.assertEqual(record.issuer, "Snowflake")
        self.assertEqual(record.credential_id, "ABC123")

    def test_existing_profile_value_is_not_overwritten_by_unrelated_extraction(self):
        profile = CareerProfile.objects.create(user=self.user)
        CareerSkill.objects.create(profile=profile, name="Python", category="Existing")
        self.confirm("skills", "name", "SQL")
        self.assertEqual(profile.careerskill_records.get(name="Python").category, "Existing")
        self.assertTrue(profile.careerskill_records.filter(name="SQL").exists())

    def test_other_user_cannot_confirm_interview_extraction(self):
        extraction = AIExtraction.objects.create(
            conversation=self.conversation,
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
        response = self.client.get(reverse("cv:career_interview_conversation", kwargs={"conversation_id": self.conversation.pk}))
        self.assertEqual(response.status_code, 200)
        other_conversation = AIConversation.objects.create(owner=self.other_user, purpose=AIConversation.PURPOSE_INTERVIEW)
        response = self.client.get(reverse("cv:career_interview_conversation", kwargs={"conversation_id": other_conversation.pk}))
        self.assertEqual(response.status_code, 404)

    def test_profile_is_created_for_interview_entry_point(self):
        CareerProfile.objects.filter(user=self.user).delete()
        response = self.client.get(reverse("cv:career_interview"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CareerProfile.objects.filter(user=self.user).exists())
