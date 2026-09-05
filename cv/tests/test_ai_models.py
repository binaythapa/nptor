from django.contrib.auth import get_user_model
from django.test import TestCase

from cv.models import ATSAnalysis, AIConversation, AIExtraction, AIMessage
from cv.services.profile import get_or_create_career_profile


class AIModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ai-user", email="ai@example.com", password="pass"
        )
        self.other = get_user_model().objects.create_user(
            username="other-ai", email="other@example.com", password="pass"
        )
        self.profile = get_or_create_career_profile(self.user)

    def test_conversation_and_message_are_owned_by_user(self):
        conversation = AIConversation.objects.create(
            owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW
        )
        message = AIMessage.objects.create(
            conversation=conversation, role=AIMessage.ROLE_USER, content="Tell me about your work."
        )
        self.assertEqual(conversation.owner_id, self.user.id)
        self.assertEqual(message.conversation.owner_id, self.user.id)

    def test_extraction_starts_unconfirmed(self):
        conversation = AIConversation.objects.create(owner=self.user)
        message = AIMessage.objects.create(
            conversation=conversation, role=AIMessage.ROLE_ASSISTANT, content="I found a possible skill."
        )
        extraction = AIExtraction.objects.create(
            conversation=conversation,
            source_message=message,
            section="skills",
            field_name="name",
            proposed_value={"name": "Python"},
        )
        self.assertFalse(extraction.confirmed)
        self.assertIsNone(extraction.confirmed_by_id)

    def test_ats_analysis_belongs_to_conversation_owner(self):
        conversation = AIConversation.objects.create(owner=self.user)
        analysis = ATSAnalysis.objects.create(
            owner=self.user,
            conversation=conversation,
            score=82,
            result={"strengths": ["clear skills"]},
        )
        self.assertEqual(analysis.owner_id, self.user.id)
        self.assertEqual(analysis.conversation.owner_id, self.user.id)

    def test_ai_records_are_separated_by_owner(self):
        first = AIConversation.objects.create(owner=self.user)
        second = AIConversation.objects.create(owner=self.other)
        self.assertNotEqual(first.owner_id, second.owner_id)
