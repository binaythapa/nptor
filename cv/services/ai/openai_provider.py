import json
import os

import requests

from cv.services.ai.provider import AIProvider, AIProviderNotConfigured


class OpenAIProvider(AIProvider):
    name = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key=None, model=None, timeout=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
        self.model = model or os.environ.get("CV_AI_MODEL", "gpt-5.6-luna").strip()
        self.timeout = int(timeout or os.environ.get("CV_AI_TIMEOUT_SECONDS", "60"))

    def _request(self, input_text, *, system_prompt="", model=None, schema=None):
        if not self.api_key:
            raise AIProviderNotConfigured("OPENAI_API_KEY is not configured.")
        payload = {"model": model or self.model, "input": input_text}
        if system_prompt:
            payload["instructions"] = system_prompt
        if schema:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "cv_ai_result",
                    "strict": True,
                    "schema": schema,
                }
            }
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise requests.HTTPError(
                    f"OpenAI Responses API returned HTTP {response.status_code}: {detail}",
                    response=response,
                ) from exc
            raise
        return response.json()

    @staticmethod
    def _output_text(response):
        output_text = response.get("output_text")
        if output_text:
            return output_text
        chunks = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    chunks.append(text)
        if not chunks:
            raise ValueError("OpenAI response did not contain text output.")
        return "".join(chunks)

    def generate_text(self, prompt, *, system_prompt="", model=None):
        return self._output_text(self._request(prompt, system_prompt=system_prompt, model=model))

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        text = self._output_text(self._request(prompt, system_prompt=system_prompt, model=model, schema=schema))
        return json.loads(text)
