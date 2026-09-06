import json
import os
from copy import deepcopy
from urllib import error, request

from django.db import transaction
from django.utils import timezone

from cv.models_ai import AIConversation, AIMessage, AISuggestion, ATSAnalysis
from cv.services.cv_builder import build_cv_payload, create_cv_version


class AIProviderError(Exception):
    """Raised when the configured AI provider cannot complete a request."""


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key=None, model=None, base_url=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        if not self.api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured.")

    def _request_json(self, system, user_content):
        body = json.dumps({
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)},
            ],
        }).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (error.URLError, error.HTTPError, TimeoutError, ValueError) as exc:
            raise AIProviderError(f"AI provider request failed: {exc}") from exc
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError("AI provider returned an invalid JSON response.") from exc

    def review(self, payload):
        system = (
            "You are a professional CV reviewer. Review only the supplied CV data. "
            "Never invent employers, dates, qualifications, metrics, skills, or achievements. "
            "Return strict JSON with keys summary and suggestions. Each suggestion must contain "
            "section, field_name, kind, title, reason, current_value, proposed_value. "
            "Only suggest changes that can be represented as a string or simple JSON value."
        )
        return self._request_json(system, payload)

    def analyze_ats(self, payload, job_description):
        system = (
            "You are an ATS and recruitment analyst. Compare only the supplied CV data against "
            "the supplied job description. Never invent qualifications, employers, dates, metrics, "
            "skills, or experience. Return strict JSON with keys score, summary, keyword_match, "
            "missing_keywords, strengths, gaps, risks, recommendations. Score must be an integer 0-100. "
            "Missing keywords must be genuinely absent from the supplied CV, and recommendations must "
            "say to add something only if it is truthful."
        )
        return self._request_json(system, {"cv": payload, "job_description": job_description})

    def tailor_cv(self, payload, job_description):
        system = (
            "You are a careful CV tailoring specialist. Tailor the supplied CV only to the supplied job description. "
            "Never invent employers, dates, qualifications, metrics, skills, technologies, or achievements. "
            "Return strict JSON with keys summary and suggestions. Each suggestion must contain section, field_name, "
            "kind, title, reason, current_value, proposed_value. Only propose wording that is supported by the supplied CV. "
            "Prioritize summary and professional_title changes that improve relevance without adding unsupported facts."
        )
        return self._request_json(system, {"cv": payload, "job_description": job_description})


_provider_override = None


def set_provider_for_tests(provider):
    global _provider_override
    _provider_override = provider


def get_provider():
    return _provider_override or OpenAIProvider()


def _review_payload(payload):
    safe = deepcopy(payload)
    safe.pop("template", None)
    safe.pop("status", None)
    safe.pop("title", None)
    return safe


def _create_conversation(cv, purpose, provider, payload, result, metadata=None):
    conversation = AIConversation.objects.create(
        owner=cv.owner,
        cv=cv,
        purpose=purpose,
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=getattr(provider, "model", ""),
        metadata=metadata or {},
    )
    AIMessage.objects.create(conversation=conversation, role=AIMessage.ROLE_USER, content=json.dumps(payload, ensure_ascii=False))
    AIMessage.objects.create(conversation=conversation, role=AIMessage.ROLE_ASSISTANT, content=json.dumps(result, ensure_ascii=False))
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
    result = provider.review(payload)
    if not isinstance(result, dict):
        raise AIProviderError("AI provider returned an invalid review payload.")
    conversation = _create_conversation(cv, AIConversation.PURPOSE_REVIEW, provider, payload, result, {"review_summary": result.get("summary", "")})
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
    result = provider.analyze_ats(payload, job_description)
    if not isinstance(result, dict):
        raise AIProviderError("AI provider returned an invalid ATS payload.")
    try:
        score = max(0, min(100, int(result.get("score", 0))))
    except (TypeError, ValueError):
        raise AIProviderError("AI provider returned an invalid ATS score.")
    version = create_cv_version(cv)
    conversation = _create_conversation(
        cv,
        AIConversation.PURPOSE_JOB_MATCH,
        provider,
        {"cv": payload, "job_description": job_description},
        result,
        {"job_description": job_description, "analysis": "ats"},
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
    result = provider.tailor_cv(payload, job_description)
    if not isinstance(result, dict):
        raise AIProviderError("AI provider returned an invalid tailoring payload.")
    conversation = _create_conversation(
        cv,
        AIConversation.PURPOSE_JOB_MATCH,
        provider,
        {"cv": payload, "job_description": job_description},
        result,
        {"job_description": job_description, "analysis": "tailoring"},
    )
    _create_suggestions(conversation, result)
    return conversation


SAFE_OVERRIDE_FIELDS = {"professional_title", "summary", "linkedin_url", "portfolio_url"}


@transaction.atomic
def accept_suggestion(suggestion, user):
    conversation = suggestion.conversation
    if conversation.owner_id != user.id or not conversation.cv_id:
        raise ValueError("Suggestion does not belong to this user")
    if suggestion.status != AISuggestion.STATUS_PENDING:
        return suggestion
    if suggestion.field_name not in SAFE_OVERRIDE_FIELDS or suggestion.section not in {"summary", "profile"}:
        raise ValueError("This suggestion cannot be applied automatically")

    cv = conversation.cv
    overrides = deepcopy(cv.overrides or {})
    overrides[suggestion.field_name] = suggestion.proposed_value
    cv.overrides = overrides
    cv.save(update_fields=["overrides", "updated_at"])
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
