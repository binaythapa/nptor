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
    assistant_record = AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.ROLE_ASSISTANT,
        content=result.get("reply", ""),
    )
    extractions = []
    for fact in result.get("facts", []):
        extractions.append(
            AIExtraction.objects.create(
                conversation=conversation,
                source_message=assistant_record,
                section=fact.get("section", ""),
                field_name=fact.get("field_name", ""),
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
