from django.utils import timezone

from cv.models import AIExtraction, AIMessage
from cv.services.ai.provider import get_ai_provider
from cv.services.ai.schemas import INTERVIEW_SCHEMA


INTERVIEW_RULE = (
    "Act as a career interviewer. Ask focused follow-up questions that improve a CV. "
    "Never invent facts. Extract only facts explicitly stated by the user, and mark every "
    "extracted fact as unconfirmed until the user approves it."
)


def interview_turn(conversation, user_message, provider=None):
    if conversation.owner_id is None:
        raise ValueError("AI conversation must have an owner")
    user_message = (user_message or "").strip()
    if not user_message:
        raise ValueError("Interview message is required")

    provider = provider or get_ai_provider()
    user_record = AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.ROLE_USER,
        content=user_message,
    )
    result = provider.generate_structured(
        user_message,
        INTERVIEW_SCHEMA,
        system_prompt=INTERVIEW_RULE,
    )
    if not isinstance(result, dict) or not isinstance(result.get("facts", []), list):
        raise ValueError("AI provider returned an invalid interview response.")

    assistant_record = AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.ROLE_ASSISTANT,
        content=result.get("reply", ""),
    )
    extractions = []
    for fact in result.get("facts", []):
        if not isinstance(fact, dict) or not fact.get("section") or not fact.get("field_name"):
            continue
        extractions.append(
            AIExtraction.objects.create(
                conversation=conversation,
                source_message=assistant_record,
                section=str(fact["section"]),
                field_name=str(fact["field_name"]),
                proposed_value=fact.get("proposed_value", {}),
                confirmed=False,
            )
        )
    return {
        "reply": result.get("reply", ""),
        "next_question": result.get("next_question", ""),
        "message": assistant_record,
        "user_message": user_record,
        "extractions": extractions,
    }


def confirm_interview_extraction(extraction_id, user, value):
    extraction = AIExtraction.objects.select_related("conversation").filter(
        pk=extraction_id,
        conversation__owner=user,
        conversation__purpose=extraction_conversation_purpose(),
    ).first()
    if extraction is None:
        raise AIExtraction.DoesNotExist
    value = str(value).strip()
    if not value:
        raise ValueError("Confirmed value is required")
    extraction.proposed_value = value
    extraction.confirmed = True
    extraction.confirmed_by = user
    extraction.confirmed_at = timezone.now()
    extraction.save(update_fields=["proposed_value", "confirmed", "confirmed_by", "confirmed_at"])
    return extraction


def extraction_conversation_purpose():
    from cv.models import AIConversation

    return AIConversation.PURPOSE_INTERVIEW
