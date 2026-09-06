import json
from copy import deepcopy

import requests
from django.db import transaction
from django.utils import timezone

from cv.models import (
    CareerAchievement,
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerProject,
    CareerSkill,
)
from cv.models_ai import AIConversation, AIMessage, AISuggestion, ATSAnalysis
from cv.services.ai.provider import get_ai_provider
from cv.services.ai.schemas import (
    ATS_ANALYSIS_SCHEMA,
    CV_REVIEW_CONVERSATION_SCHEMA,
    CV_TAILOR_SCHEMA,
)
from cv.services.cv_builder import build_cv_payload, create_cv_version


class AIProviderError(Exception):
    """Raised when the configured AI provider cannot complete a request."""


_provider_override = None


def set_provider_for_tests(provider):
    global _provider_override
    _provider_override = provider


def get_provider():
    return _provider_override or get_ai_provider()


def _review_payload(payload):
    safe = deepcopy(payload)
    safe.pop("template", None)
    safe.pop("status", None)
    safe.pop("title", None)
    return safe


def _generate_structured(provider, prompt, schema, *, system_prompt):
    try:
        result = provider.generate_structured(prompt, schema, system_prompt=system_prompt)
    except requests.RequestException as exc:
        raise AIProviderError(f"AI provider request failed: {exc}") from exc
    except (TypeError, ValueError, KeyError) as exc:
        raise AIProviderError(f"AI provider returned an invalid response: {exc}") from exc
    if not isinstance(result, dict):
        raise AIProviderError("AI provider returned an invalid structured response.")
    return result


def _create_conversation(cv, purpose, provider, payload, result, metadata=None):
    conversation = AIConversation.objects.create(
        owner=cv.owner,
        cv=cv,
        purpose=purpose,
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=getattr(provider, "model", ""),
        metadata=metadata or {},
    )
    AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.ROLE_USER,
        content=json.dumps(payload, ensure_ascii=False),
    )
    AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.ROLE_ASSISTANT,
        content=json.dumps(result, ensure_ascii=False),
    )
    return conversation


def _create_suggestions(conversation, result):
    for item in result.get("suggestions", []):
        if not isinstance(item, dict) or not item.get("field_name") or not item.get("section"):
            continue
        AISuggestion.objects.create(
            conversation=conversation,
            section=str(item["section"]),
            field_name=str(item["field_name"]),
            kind=str(item.get("kind", "improvement")),
            title=str(item.get("title", "Improve this section")),
            reason=str(item.get("reason", "")),
            current_value=item.get("current_value", ""),
            proposed_value=item.get("proposed_value", ""),
        )


@transaction.atomic
def review_cv(cv, provider=None):
    if not cv.profile_id or cv.profile.user_id != cv.owner_id:
        raise ValueError("CV profile must belong to the CV owner")
    provider = provider or get_provider()
    payload = _review_payload(build_cv_payload(cv))
    result = _generate_structured(
        provider,
        "Review this CV for ATS readiness, clarity, relevance, and professional impact.\n"
        f"CV DATA:\n{json.dumps(payload, ensure_ascii=False)}",
        CV_REVIEW_CONVERSATION_SCHEMA,
        system_prompt=(
            "You are a professional CV reviewer. Review only the supplied CV data. "
            "Never invent employers, dates, qualifications, metrics, skills, or achievements. "
            "Return actionable suggestions only when they are supported by the supplied CV. "
            "Proposed wording must not introduce unsupported facts."
        ),
    )
    conversation = _create_conversation(
        cv,
        AIConversation.PURPOSE_REVIEW,
        provider,
        payload,
        result,
        {"review_summary": result.get("summary", "")},
    )
    _create_suggestions(conversation, result)
    return conversation


@transaction.atomic
def analyze_ats(cv, job_description, provider=None):
    if not cv.profile_id or cv.profile.user_id != cv.owner_id:
        raise ValueError("CV profile must belong to the CV owner")
    job_description = (job_description or "").strip()
    if not job_description:
        raise ValueError("Job description is required")
    provider = provider or get_provider()
    payload = _review_payload(build_cv_payload(cv))
    result = _generate_structured(
        provider,
        "Compare this CV with the supplied job description.\n"
        f"CV DATA:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"JOB DESCRIPTION:\n{job_description}",
        ATS_ANALYSIS_SCHEMA,
        system_prompt=(
            "You are an ATS and recruitment analyst. Compare only the supplied CV data against "
            "the supplied job description. Never invent qualifications, employers, dates, metrics, "
            "skills, or experience. Missing keywords must genuinely be absent from the supplied CV. "
            "Recommendations must say to add something only if it is truthful."
        ),
    )
    try:
        score = max(0, min(100, int(result.get("score", 0))))
    except (TypeError, ValueError) as exc:
        raise AIProviderError("AI provider returned an invalid ATS score.") from exc

    version = create_cv_version(cv)
    conversation = _create_conversation(
        cv,
        AIConversation.PURPOSE_JOB_MATCH,
        provider,
        {"cv": payload, "job_description": job_description},
        result,
        {"job_description": job_description, "analysis": "ats", "summary": result.get("summary", "")},
    )
    return ATSAnalysis.objects.create(
        owner=cv.owner,
        cv_version=version,
        conversation=conversation,
        job_description=job_description,
        score=score,
        result=result,
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=getattr(provider, "model", ""),
    )


@transaction.atomic
def tailor_cv(cv, job_description, provider=None):
    if not cv.profile_id or cv.profile.user_id != cv.owner_id:
        raise ValueError("CV profile must belong to the CV owner")
    job_description = (job_description or "").strip()
    if not job_description:
        raise ValueError("Job description is required")
    provider = provider or get_provider()
    payload = _review_payload(build_cv_payload(cv))
    result = _generate_structured(
        provider,
        "Tailor this CV for the supplied job description without inventing facts.\n"
        f"CV DATA:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"JOB DESCRIPTION:\n{job_description}",
        CV_TAILOR_SCHEMA,
        system_prompt=(
            "You are a careful CV tailoring specialist. Tailor only the wording supported by the supplied CV. "
            "Never invent employers, dates, qualifications, metrics, skills, technologies, or achievements. "
            "Prioritize summary and professional title changes that improve relevance without adding unsupported facts."
        ),
    )
    conversation = _create_conversation(
        cv,
        AIConversation.PURPOSE_JOB_MATCH,
        provider,
        {"cv": payload, "job_description": job_description},
        result,
        {"job_description": job_description, "analysis": "tailoring", "summary": result.get("summary", "")},
    )
    _create_suggestions(conversation, result)
    return conversation


SAFE_OVERRIDE_FIELDS = {"professional_title", "summary", "linkedin_url", "portfolio_url"}
SAFE_OVERRIDE_SECTIONS = {
    "summary": {"summary"},
    "profile": SAFE_OVERRIDE_FIELDS,
    "professional_title": {"professional_title"},
}
RECORD_SUGGESTION_FIELDS = {
    "experiences": (CareerExperience, {"job_title", "employer", "location", "description"}),
    "educations": (CareerEducation, {"institution", "qualification", "field_of_study", "location", "description"}),
    "projects": (CareerProject, {"name", "role", "url", "description", "technologies"}),
    "skills": (CareerSkill, {"name", "category", "proficiency"}),
    "achievements": (CareerAchievement, {"title", "description"}),
    "certifications": (CareerCertification, {"name", "issuer", "credential_id", "credential_url"}),
}


def _apply_record_suggestion(suggestion, user):
    config = RECORD_SUGGESTION_FIELDS.get(suggestion.section)
    if config is None:
        raise ValueError("This suggestion cannot be applied automatically")

    model, allowed_fields = config
    if suggestion.field_name not in allowed_fields:
        raise ValueError("This suggestion field cannot be applied automatically")

    profile = suggestion.conversation.cv.profile
    if profile.user_id != user.id:
        raise ValueError("Suggestion does not belong to this user")

    current_value = suggestion.current_value
    proposed_value = suggestion.proposed_value
    if not isinstance(current_value, str) or not isinstance(proposed_value, str):
        raise ValueError("This suggestion has an unsupported value format")
    current_value = current_value.strip()
    proposed_value = proposed_value.strip()
    if not current_value or not proposed_value:
        raise ValueError("This suggestion must contain both current and proposed text")

    matches = model.objects.filter(profile=profile, **{suggestion.field_name: current_value})
    count = matches.count()
    if count == 0:
        raise ValueError("The original profile value could not be found. Refresh the AI review and try again.")
    if count > 1:
        raise ValueError("More than one profile record has this value. This suggestion needs manual review.")

    record = matches.first()
    setattr(record, suggestion.field_name, proposed_value)
    record.save(update_fields=[suggestion.field_name, "updated_at"])


@transaction.atomic
def accept_suggestion(suggestion, user):
    conversation = suggestion.conversation
    if conversation.owner_id != user.id or not conversation.cv_id:
        raise ValueError("Suggestion does not belong to this user")
    if suggestion.status != AISuggestion.STATUS_PENDING:
        return suggestion

    allowed_fields = SAFE_OVERRIDE_SECTIONS.get(suggestion.section, set())
    if suggestion.field_name in SAFE_OVERRIDE_FIELDS and suggestion.field_name in allowed_fields:
        cv = conversation.cv
        overrides = deepcopy(cv.overrides or {})
        overrides[suggestion.field_name] = suggestion.proposed_value
        cv.overrides = overrides
        cv.save(update_fields=["overrides", "updated_at"])
    elif suggestion.section in RECORD_SUGGESTION_FIELDS:
        _apply_record_suggestion(suggestion, user)
    else:
        raise ValueError("This suggestion cannot be applied automatically")

    suggestion.status = AISuggestion.STATUS_ACCEPTED
    suggestion.accepted = True
    suggestion.acted_at = timezone.now()
    suggestion.save(update_fields=["status", "accepted", "acted_at"])
    return suggestion


@transaction.atomic
def reject_suggestion(suggestion, user):
    if suggestion.conversation.owner_id != user.id:
        raise ValueError("Suggestion does not belong to this user")
    if suggestion.status == AISuggestion.STATUS_PENDING:
        suggestion.status = AISuggestion.STATUS_REJECTED
        suggestion.accepted = False
        suggestion.acted_at = timezone.now()
        suggestion.save(update_fields=["status", "accepted", "acted_at"])
    return suggestion
