import os
from unittest.mock import patch

from django.test import SimpleTestCase

from cv.services.ai.provider import AIProviderNotConfigured, get_ai_provider


class AIProviderTests(SimpleTestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_provider_is_unconfigured_without_api_key(self):
        provider = get_ai_provider()
        with self.assertRaises(AIProviderNotConfigured):
            provider.generate_text("hello")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_provider_factory_can_create_openai_provider(self):
        provider = get_ai_provider()
        self.assertEqual(provider.name, "openai")

    def test_structured_schema_has_truth_constraint(self):
        from cv.services.ai.schemas import CAREER_FACT_SCHEMA
        self.assertIn("confirmed", CAREER_FACT_SCHEMA["properties"])
        self.assertIn("evidence", CAREER_FACT_SCHEMA["properties"])
