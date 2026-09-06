import json
import logging
import os
import re

import requests

from cv.services.ai.provider import AIProvider, AIProviderNotConfigured, AIProviderRateLimited


logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    name = "gemini"
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key=None, model=None, timeout=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = model or os.environ.get("CV_AI_MODEL", "gemini-3.6-flash").strip()
        self.timeout = int(timeout or os.environ.get("CV_AI_TIMEOUT_SECONDS", "60"))

    @staticmethod
    def _retry_after_seconds(error_body):
        for detail in error_body.get("error", {}).get("details", []):
            if not isinstance(detail, dict):
                continue
            retry_delay = detail.get("retryDelay")
            if not isinstance(retry_delay, str):
                continue
            match = re.fullmatch(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?", retry_delay.strip())
            if not match or not any(match.groups()):
                continue
            hours, minutes, seconds = (float(value or 0) for value in match.groups())
            return int(hours * 3600 + minutes * 60 + seconds)
        return None

    def _request(self, input_text, *, system_prompt="", model=None, schema=None):
        if not self.api_key:
            raise AIProviderNotConfigured("GEMINI_API_KEY is not configured.")

        generation_config = {}
        if schema:
            generation_config["response_mime_type"] = "application/json"
            # `response_schema` is Gemini's OpenAPI-like Schema type and does not
            # accept JSON Schema keywords such as `additionalProperties`.
            # `responseJsonSchema` accepts the JSON Schema subset used by our
            # shared provider schemas, including nested additionalProperties.
            generation_config["responseJsonSchema"] = schema

        payload = {
            "contents": [{"role": "user", "parts": [{"text": input_text}]}],
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        if generation_config:
            payload["generationConfig"] = generation_config

        selected_model = model or self.model
        url = self.endpoint.format(model=selected_model)
        response = requests.post(
            url,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 429:
                try:
                    error_body = response.json()
                except ValueError:
                    error_body = {}
                retry_after = self._retry_after_seconds(error_body)
                logger.warning(
                    "Gemini request rate-limited: provider=%s model=%s status=%s retry_after=%s",
                    self.name,
                    selected_model,
                    response.status_code,
                    retry_after,
                )
                raise AIProviderRateLimited(
                    "Gemini API quota is currently exhausted. Please try again later or check your Gemini API plan and billing.",
                    provider=self.name,
                    retry_after_seconds=retry_after,
                ) from exc

            logger.warning(
                "Gemini request failed: provider=%s model=%s status=%s",
                self.name,
                selected_model,
                response.status_code,
            )
            raise requests.HTTPError(
                f"Gemini API request failed with HTTP {response.status_code}",
                response=response,
            ) from exc
        return response.json()

    @staticmethod
    def _output_text(response):
        for candidate in response.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    return text
        raise ValueError("Gemini response did not contain text output.")

    def generate_text(self, prompt, *, system_prompt="", model=None):
        return self._output_text(self._request(prompt, system_prompt=system_prompt, model=model))

    def generate_structured(self, prompt, schema, *, system_prompt="", model=None):
        text = self._output_text(
            self._request(prompt, system_prompt=system_prompt, model=model, schema=schema)
        )
        return json.loads(text)
