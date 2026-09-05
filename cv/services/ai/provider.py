import os


class AIProviderNotConfigured(RuntimeError):
    """Raised when an optional AI provider has not been configured."""


class AIProvider:
    name = "base"

    def generate_text(self, prompt, *, system_prompt="", model=None):
        raise NotImplementedError

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        raise NotImplementedError


def get_ai_provider():
    provider_name = os.environ.get("CV_AI_PROVIDER", "openai").strip().lower()
    if provider_name == "openai":
        from cv.services.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if provider_name in {"", "none", "disabled"}:
        return _UnavailableProvider()
    raise AIProviderNotConfigured(f"Unsupported CV AI provider: {provider_name}")


class _UnavailableProvider(AIProvider):
    name = "none"

    def generate_text(self, prompt, *, system_prompt="", model=None):
        raise AIProviderNotConfigured("No CV AI provider is configured.")

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        raise AIProviderNotConfigured("No CV AI provider is configured.")
