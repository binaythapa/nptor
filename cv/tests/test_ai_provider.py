import json
import os
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from cv.services.ai.provider import AIProviderNotConfigured, get_ai_provider


class AIProviderTests(SimpleTestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_provider_is_unconfigured_by_default(self):
        provider = get_ai_provider()
        self.assertEqual(provider.name, "none")
        with self.assertRaises(AIProviderNotConfigured):
            provider.generate_text("hello")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "CV_AI_PROVIDER": "openai"}, clear=True)
    def test_provider_factory_can_create_openai_provider(self):
        provider = get_ai_provider()
        self.assertEqual(provider.name, "openai")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "CV_AI_PROVIDER": "gemini"}, clear=True)
    def test_provider_factory_can_create_gemini_provider(self):
        provider = get_ai_provider()
        self.assertEqual(provider.name, "gemini")

    @patch.dict(os.environ, {"CV_AI_PROVIDER": "ollama"}, clear=True)
    def test_provider_factory_can_create_ollama_provider(self):
        provider = get_ai_provider()
        self.assertEqual(provider.name, "ollama")

    def test_structured_schema_has_truth_constraint(self):
        from cv.services.ai.schemas import CAREER_FACT_SCHEMA
        self.assertIn("confirmed", CAREER_FACT_SCHEMA["properties"])
        self.assertIn("evidence", CAREER_FACT_SCHEMA["properties"])

    def test_career_fact_schema_uses_supported_strict_json_types(self):
        from cv.services.ai.schemas import CAREER_FACT_SCHEMA
        self.assertEqual(CAREER_FACT_SCHEMA["properties"]["proposed_value"], {"type": "string"})

    @patch("cv.services.ai.openai_provider.requests.post")
    def test_openai_provider_surfaces_responses_api_error_body(self, post):
        from cv.services.ai.openai_provider import OpenAIProvider

        response = requests.Response()
        response.status_code = 400
        response._content = b'{"error":{"message":"Invalid schema"}}'
        post.return_value = response

        provider = OpenAIProvider(api_key="test-key")
        with self.assertRaisesRegex(requests.HTTPError, "Invalid schema"):
            provider.generate_structured("hello", {"type": "object"})

    @patch("cv.services.ai.gemini_provider.requests.post")
    def test_gemini_provider_supports_structured_output(self, post):
        from cv.services.ai.gemini_provider import GeminiProvider

        response = requests.Response()
        response.status_code = 200
        response._content = b'{"candidates":[{"content":{"parts":[{"text":"{\\"ok\\":true}"}]}}]}'
        post.return_value = response

        schema = {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "additionalProperties": False,
        }
        provider = GeminiProvider(api_key="test-key")
        result = provider.generate_structured("hello", schema)

        self.assertEqual(result, {"ok": True})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["generationConfig"]["response_mime_type"], "application/json")
        self.assertEqual(payload["generationConfig"]["responseJsonSchema"], schema)
        self.assertNotIn("response_schema", payload["generationConfig"])

    @patch("cv.services.ai.gemini_provider.requests.post")
    def test_gemini_provider_converts_quota_429_to_safe_rate_limit_error(self, post):
        from cv.services.ai.gemini_provider import GeminiProvider
        from cv.services.ai.provider import AIProviderRateLimited

        response = requests.Response()
        response.status_code = 429
        response._content = json.dumps(
            {
                "error": {
                    "code": 429,
                    "message": "You exceeded your current quota, please check your plan and billing details.",
                    "status": "RESOURCE_EXHAUSTED",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "30s",
                        }
                    ],
                }
            }
        ).encode()
        post.return_value = response

        provider = GeminiProvider(api_key="test-key")
        with self.assertRaises(AIProviderRateLimited) as context:
            provider.generate_text("hello")

        self.assertEqual(context.exception.provider, "gemini")
        self.assertEqual(context.exception.retry_after_seconds, 30)
        self.assertEqual(str(context.exception), "Gemini API quota is currently exhausted. Please try again later or check your Gemini API plan and billing.")
        self.assertNotIn("RESOURCE_EXHAUSTED", str(context.exception))
        self.assertNotIn("test-key", str(context.exception))

    @patch("cv.services.ai.gemini_provider.requests.post")
    def test_gemini_provider_hides_raw_body_for_other_http_errors(self, post):
        from cv.services.ai.gemini_provider import GeminiProvider

        response = requests.Response()
        response.status_code = 403
        response._content = b'{"error":{"message":"secret provider detail"}}'
        post.return_value = response

        provider = GeminiProvider(api_key="test-key")
        with self.assertRaisesRegex(requests.HTTPError, "Gemini API request failed with HTTP 403") as context:
            provider.generate_text("hello")

        self.assertNotIn("secret provider detail", str(context.exception))
        self.assertNotIn("test-key", str(context.exception))

    @patch("cv.services.ai.gemini_provider.requests.post")
    def test_gemini_provider_preserves_retryable_error_when_retry_info_is_malformed(self, post):
        from cv.services.ai.gemini_provider import GeminiProvider
        from cv.services.ai.provider import AIProviderRateLimited

        response = requests.Response()
        response.status_code = 429
        response._content = b'{"error":{"code":429,"message":"quota exceeded","details":[{"retryDelay":"not-a-duration"}]}}'
        post.return_value = response

        provider = GeminiProvider(api_key="test-key")
        with self.assertRaises(AIProviderRateLimited) as context:
            provider.generate_text("hello")

        self.assertIsNone(context.exception.retry_after_seconds)

    @patch("cv.services.ai.ollama_provider.requests.post")
    def test_ollama_provider_supports_structured_output(self, post):
        from cv.services.ai.ollama_provider import OllamaProvider

        response = requests.Response()
        response.status_code = 200
        response._content = b'{"message":{"content":"{\\"ok\\":true}"}}'
        post.return_value = response

        provider = OllamaProvider(base_url="http://localhost:11434", model="test-model")
        result = provider.generate_structured("hello", {"type": "object", "properties": {"ok": {"type": "boolean"}}})

        self.assertEqual(result, {"ok": True})
        payload = post.call_args.kwargs["json"]
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["format"]["type"], "object")
