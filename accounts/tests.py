from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import EmailOTP


class AdminBaseTemplateTests(SimpleTestCase):
    def test_admin_base_loads_bulma_stylesheet(self):
        template = get_template("layouts/admin/base_admin.html")

        self.assertIn(
            'https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css',
            template.template.source,
        )


class LoginOTPRegressionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="otpuser",
            email="otpuser@example.com",
            password="secret-password",
        )
        self.request_otp_url = reverse("accounts:request-login-otp")

    def test_get_request_login_otp_page_returns_200(self):
        response = self.client.get(self.request_otp_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="email"', html=False)

    def test_post_request_otp_nonexistent_email_returns_safe_message(self):
        response = self.client.post(
            self.request_otp_url,
            {"email": "unknown@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "If an account exists with this email, a login OTP will be sent.",
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailOTP.objects.count(), 0)

    def test_post_request_otp_success_creates_otp_and_redirects(self):
        response = self.client.post(
            self.request_otp_url,
            {"email": "otpuser@example.com"},
        )
        self.assertRedirects(response, reverse("accounts:verify-login-otp"))
        self.assertEqual(self.client.session.get("otp_user_id"), self.user.id)

        otp = EmailOTP.objects.filter(
            user=self.user,
            purpose=EmailOTP.PURPOSE_LOGIN,
        ).first()
        self.assertIsNotNone(otp)
        self.assertEqual(otp.email, "otpuser@example.com")
        self.assertFalse(otp.is_used)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(otp.email, mail.outbox[0].to)

    def test_post_request_otp_cooldown_throttles_rapid_requests(self):
        # First request succeeds
        self.client.post(
            self.request_otp_url,
            {"email": "otpuser@example.com"},
        )
        self.assertEqual(EmailOTP.objects.count(), 1)

        # Second request within 30s should be rejected
        response = self.client.post(
            self.request_otp_url,
            {"email": "otpuser@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Please wait 30 seconds before requesting another OTP.",
        )
        self.assertEqual(EmailOTP.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_post_request_otp_service_failure_does_not_500(self):
        with patch("accounts.views.login.create_login_otp", side_effect=RuntimeError("SMTP connection failed")):
            response = self.client.post(
                self.request_otp_url,
                {"email": "otpuser@example.com"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response,
                "Unable to send verification code. Please try again in a few moments.",
            )
            self.assertNotIn("otp_user_id", self.client.session)
