import json
import os

import requests

from cv.services.ai.provider import AIProvider, AIProviderNotConfigured


class OllamaProvider(AIProvider):
    name = "ollama"
    endpoint = "/api/chat"

    def __init__(self, base_url=None, model=None, timeout=None):
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.environ.get("CV_AI_MODEL", "llama3.2:3b").strip()
        self.timeout = int(timeout or os.environ.get("CV_AI_TIMEOUT_SECONDS", "120"))

    def _request(self, input_text, *, system_prompt="", model=None, schema=None):
        if not self.base_url:
            raise AIProviderNotConfigured("OLLAMA_BASE_URL is not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "format": schema or "json",
            "options": {"temperature": 0},
        }
        response = requests.post(
            f"{self.base_url}{self.endpoint}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise requests.HTTPError(
                    f"Ollama API returned HTTP {response.status_code}: {detail}",
                    response=response,
                ) from exc
            raise
        return response.json()

    @staticmethod
    def _output_text(response):
        text = response.get("message", {}).get("content")
        if not text:
            raise ValueError("Ollama response did not contain text output.")
        return text

    def generate_text(self, prompt, *, system_prompt="", model=None):
        return self._output_text(self._request(prompt, system_prompt=system_prompt, model=model))

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        text = self._output_text(
            self._request(prompt, system_prompt=system_prompt, model=model, schema=schema)
        )
        return json.loads(text)
