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
