from pathlib import Path
from django.test import SimpleTestCase


class SecuritySettingsSourceTests(SimpleTestCase):
    """Regression tests for secrets and production cookie settings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings_source = (
            Path(__file__).resolve().parent / "settings.py"
        ).read_text(encoding="utf-8-sig")

    def test_secret_key_has_no_hardcoded_fallback(self):
        self.assertNotIn("django-insecure-change-me-please", self.settings_source)
        self.assertIn(
            'SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")',
            self.settings_source,
        )
        self.assertIn(
            'raise RuntimeError("DJANGO_SECRET_KEY must be set in the environment.")',
            self.settings_source,
        )

    def test_email_password_is_environment_configured(self):
        self.assertNotIn("EMAIL_HOST_PASSWORD = '" , self.settings_source)
        self.assertNotIn('EMAIL_HOST_PASSWORD = "', self.settings_source)
        self.assertIn(
            'EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")',
            self.settings_source,
        )

    def test_session_cookie_samesite_is_not_overridden_to_none(self):
        self.assertEqual(
            self.settings_source.count("SESSION_COOKIE_SAMESITE ="),
            1,
        )
        self.assertIn('SESSION_COOKIE_SAMESITE = "Lax"', self.settings_source)
