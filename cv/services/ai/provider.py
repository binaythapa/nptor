import os


class AIProviderNotConfigured(RuntimeError):
    """Raised when an optional AI provider has not been configured."""


class AIProviderRateLimited(AIProviderNotConfigured):
    """Raised when an AI provider refuses a request because of rate limits/quota."""

    def __init__(self, message, *, provider, retry_after_seconds=None):
        super().__init__(message)
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds


class AIProvider:
    name = "base"

    def generate_text(self, prompt, *, system_prompt="", model=None):
        raise NotImplementedError

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        raise NotImplementedError


def get_ai_provider():
    # Safe default: never accidentally incur API charges in an unconfigured environment.
    provider_name = os.environ.get("CV_AI_PROVIDER", "none").strip().lower()
    if provider_name == "openai":
        from cv.services.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if provider_name == "gemini":
        from cv.services.ai.gemini_provider import GeminiProvider
        return GeminiProvider()
    if provider_name == "ollama":
        from cv.services.ai.ollama_provider import OllamaProvider
        return OllamaProvider()
    if provider_name in {"", "none", "disabled"}:
        return _UnavailableProvider()
    raise AIProviderNotConfigured(f"Unsupported CV AI provider: {provider_name}")


class _UnavailableProvider(AIProvider):
    name = "none"

    def generate_text(self, prompt, *, system_prompt="", model=None):
        raise AIProviderNotConfigured("No CV AI provider is configured.")

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        raise AIProviderNotConfigured("No CV AI provider is configured.")
