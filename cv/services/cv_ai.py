import json
import os
from copy import deepcopy
from urllib import error, request

from django.db import transaction
from django.utils import timezone

from cv.models_ai import AIConversation, AIMessage, AISuggestion
from cv.services.cv_builder import build_cv_payload


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

    def review(self, payload):
        system = (
            "You are a professional CV reviewer. Review only the supplied CV data. "
            "Never invent employers, dates, qualifications, metrics, skills, or achievements. "
            "Return strict JSON with keys summary and suggestions. Each suggestion must contain "
            "section, field_name, kind, title, reason, current_value, proposed_value. "
            "Only suggest changes that can be represented as a string or simple JSON value."
        )
        body = json.dumps({
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
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
            raise AIProviderError("AI provider returned an invalid review response.") from exc


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


@transaction.atomic
def review_cv(cv, provider=None):
    if not cv.profile_id or cv.profile.user_id != cv.owner_id:
        raise ValueError("CV profile must belong to the CV owner")
    provider = provider or get_provider()
    payload = _review_payload(build_cv_payload(cv))
    result = provider.review(payload)
    if not isinstance(result, dict):
        raise AIProviderError("AI provider returned an invalid review payload.")

    conversation = AIConversation.objects.create(
        owner=cv.owner,
        cv=cv,
        purpose=AIConversation.PURPOSE_REVIEW,
        provider=getattr(provider, "name", provider.__class__.__name__),
        model=getattr(provider, "model", ""),
        metadata={"review_summary": result.get("summary", "")},
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
