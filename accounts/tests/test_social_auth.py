from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from allauth.socialaccount.providers.google.provider import GoogleProvider

from accounts.adapters import NPTORSocialAccountAdapter
from accounts.models import EmailOTP, UserProfile

User = get_user_model()


class GoogleSocialAuthTests(TestCase):
    """
    Comprehensive regression tests for NPTOR Google OAuth 2.0 social login:
    - Routing and URLs
    - OAuth state and CSRF protection
    - Conditional login button visibility
    - Verified identity enforcement
    - Unverified email rejection (account takeover prevention)
    - Safe account linking preserving existing user data, permissions, and passwords
    - Inactive user protection
    - Integration with existing OTP login flow
    """

    def setUp(self):
        self.client = Client()
        self.rf = RequestFactory()
        self.test_oauth_settings = {
            "google": {
                "APP": {
                    "client_id": "test-google-client-id.apps.googleusercontent.com",
                    "secret": "test-google-client-secret-123",
                    "key": "",
                },
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
                "EMAIL_AUTHENTICATION": True,
            }
        }

    def _prepare_request(self, req, user=None):
        sm = SessionMiddleware(lambda r: None)
        sm.process_request(req)
        req.session.save()
        mm = MessageMiddleware(lambda r: None)
        mm.process_request(req)
        if user:
            req.user = user
        return req

    def test_google_login_urls_and_routing(self):
        """Verify social login and callback URLs reverse and resolve correctly."""
        login_url = reverse("google_login")
        callback_url = reverse("google_callback")
        self.assertEqual(login_url, "/social/google/login/")
        self.assertEqual(callback_url, "/social/google/login/callback/")

    def test_oauth_state_and_csrf_validation(self):
        """Direct callback access without valid OAuth state must reject with HTTP 401."""
        with override_settings(
            ALLOWED_HOSTS=["testserver", "localhost"],
            GOOGLE_OAUTH_CLIENT_ID="test-client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="test-client-secret",
            SOCIALACCOUNT_PROVIDERS=self.test_oauth_settings,
        ):
            resp = self.client.get("/social/google/login/callback/")
            self.assertEqual(resp.status_code, 401)

    def test_oauth_initiation_redirect(self):
        """POST to google_login initiates redirect to Google OAuth with state parameter."""
        with override_settings(
            ALLOWED_HOSTS=["testserver", "localhost"],
            GOOGLE_OAUTH_CLIENT_ID="test-google-client-id.apps.googleusercontent.com",
            GOOGLE_OAUTH_CLIENT_SECRET="test-google-client-secret-123",
            SOCIALACCOUNT_PROVIDERS=self.test_oauth_settings,
        ):
            resp = self.client.post("/social/google/login/")
            self.assertEqual(resp.status_code, 302)
            redirect_url = resp.get("Location", "")
            self.assertIn("accounts.google.com/o/oauth2/v2/auth", redirect_url)
            self.assertIn("client_id=test-google-client-id.apps.googleusercontent.com", redirect_url)
            self.assertTrue("scope=email+profile" in redirect_url or "scope=profile+email" in redirect_url)
            self.assertIn("state=", redirect_url)
            self.assertIn("%2Fsocial%2Fgoogle%2Flogin%2Fcallback%2F", redirect_url)

    def test_conditional_button_visibility(self):
        """The Continue with Google button appears only when credentials are configured."""
        # 1. Unset credentials -> Button hidden
        with override_settings(
            ALLOWED_HOSTS=["testserver", "localhost"],
            GOOGLE_OAUTH_CLIENT_ID="",
            GOOGLE_OAUTH_CLIENT_SECRET="",
        ):
            resp = self.client.get("/accounts/login/otp/request/")
            self.assertEqual(resp.status_code, 200)
            self.assertNotContains(resp, "Continue with Google")

        # 2. Set credentials -> Button visible with correct link
        with override_settings(
            ALLOWED_HOSTS=["testserver", "localhost"],
            GOOGLE_OAUTH_CLIENT_ID="test-google-client-id.apps.googleusercontent.com",
            GOOGLE_OAUTH_CLIENT_SECRET="test-google-client-secret-123",
            SOCIALACCOUNT_PROVIDERS=self.test_oauth_settings,
        ):
            resp = self.client.get("/accounts/login/otp/request/")
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "Continue with Google")
            self.assertContains(resp, "/social/google/login/?process=login")

    def test_adapter_registration(self):
        """Verify NPTORSocialAccountAdapter is registered as the active allauth adapter."""
        adapter = get_adapter()
        self.assertIsInstance(adapter, NPTORSocialAccountAdapter)

    def test_new_user_signup_with_verified_google_identity(self):
        """New user authenticating with verified Google identity gets username=email and verified UserProfile."""
        adapter = get_adapter()
        req = self._prepare_request(self.rf.get("/"))

        social_account = SocialAccount(provider="google", uid="google-uid-new-101")
        verified_email = EmailAddress(
            email="newstudent@gmail.com",
            verified=True,
            primary=True,
        )
        sociallogin = SocialLogin(
            account=social_account,
            email_addresses=[verified_email],
        )
        sociallogin.user = User()

        user_data = {
            "email": "newstudent@gmail.com",
            "first_name": "New",
            "last_name": "Student",
        }

        # Adapter populate
        user = adapter.populate_user(req, sociallogin, user_data)
        self.assertEqual(user.username, "newstudent@gmail.com")
        self.assertEqual(user.email, "newstudent@gmail.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        # Adapter save
        sociallogin.user = user
        saved_user = adapter.save_user(req, sociallogin)
        self.assertEqual(saved_user.username, "newstudent@gmail.com")
        self.assertFalse(saved_user.has_usable_password())

        # Verify UserProfile email_verified state
        profile = UserProfile.objects.get(user=saved_user)
        self.assertTrue(profile.email_verified)

    def test_unverified_email_identity_rejected(self):
        """Unverified email from Google must be rejected to prevent account takeover."""
        adapter = get_adapter()
        req = self._prepare_request(self.rf.get("/"))

        social_account = SocialAccount(provider="google", uid="google-uid-unverified-400")
        unverified_email = EmailAddress(
            email="unverified@gmail.com",
            verified=False,  # Unverified!
            primary=True,
        )
        sociallogin = SocialLogin(
            account=social_account,
            email_addresses=[unverified_email],
        )

        with self.assertRaises(ImmediateHttpResponse) as cm:
            adapter.pre_social_login(req, sociallogin)

        # Redirects safely to login
        self.assertEqual(cm.exception.response.url, reverse("accounts:request-login-otp"))

    def test_existing_account_linking_preserves_password_data_and_permissions(self):
        """Existing user linking Google preserves their password, staff status, and profile."""
        existing_user = User.objects.create_user(
            username="existing.teacher@nptor.com",
            email="existing.teacher@nptor.com",
            first_name="Prof",
            last_name="Teacher",
            is_staff=True,
        )
        existing_user.set_password("SecurePassword999!")
        existing_user.save()

        # Existing profile
        profile, _ = UserProfile.objects.get_or_create(user=existing_user)
        profile.country = "NP"
        profile.address = "Kathmandu, Bagmati"
        profile.email_verified = False  # Initially false
        profile.save()

        adapter = get_adapter()
        req = self._prepare_request(self.rf.get("/"))

        social_account = SocialAccount(provider="google", uid="google-uid-teacher-555")
        verified_email = EmailAddress(
            email="existing.teacher@nptor.com",
            verified=True,
            primary=True,
        )
        sociallogin = SocialLogin(
            account=social_account,
            email_addresses=[verified_email],
        )
        sociallogin.user = existing_user

        # Run pre_social_login
        adapter.pre_social_login(req, sociallogin)

        # User is preserved
        existing_user.refresh_from_db()
        self.assertEqual(existing_user.pk, sociallogin.user.pk)
        self.assertTrue(existing_user.has_usable_password(), "Native password must NOT be wiped")
        self.assertTrue(existing_user.is_staff, "Staff role must NOT be altered")
        self.assertTrue(existing_user.check_password("SecurePassword999!"))

        # Profile is preserved and verified
        profile.refresh_from_db()
        self.assertEqual(str(profile.country), "NP")
        self.assertEqual(profile.address, "Kathmandu, Bagmati")
        self.assertTrue(profile.email_verified, "Profile email_verified should now be True")

        # Duplicate account prevented
        self.assertEqual(User.objects.filter(email="existing.teacher@nptor.com").count(), 1)

    def test_inactive_account_blocked_from_social_login(self):
        """Deactivated user account cannot log in via Google."""
        inactive_user = User.objects.create_user(
            username="banned@example.com",
            email="banned@example.com",
            is_active=False,
        )

        adapter = get_adapter()
        req = self._prepare_request(self.rf.get("/"))

        sociallogin = SocialLogin(
            account=SocialAccount(provider="google", uid="banned-uid"),
            email_addresses=[EmailAddress(email="banned@example.com", verified=True)],
        )
        sociallogin.user = inactive_user

        with self.assertRaises(ImmediateHttpResponse) as cm:
            adapter.pre_social_login(req, sociallogin)

        self.assertEqual(cm.exception.response.url, reverse("accounts:request-login-otp"))

    def test_authenticated_user_connecting_mismatched_email_rejected(self):
        """Logged-in user trying to connect a mismatched Google email is safely rejected."""
        logged_in_user = User.objects.create_user(
            username="student1@nptor.com",
            email="student1@nptor.com",
        )

        adapter = get_adapter()
        req = self._prepare_request(self.rf.get("/"), user=logged_in_user)

        # Mismatched Google email
        sociallogin = SocialLogin(
            account=SocialAccount(provider="google", uid="other-uid"),
            email_addresses=[EmailAddress(email="someone.else@gmail.com", verified=True)],
        )

        with self.assertRaises(ImmediateHttpResponse) as cm:
            adapter.pre_social_login(req, sociallogin)

        self.assertEqual(cm.exception.response.url, reverse("accounts:request-login-otp"))

    def test_existing_email_otp_login_regression(self):
        """Native email OTP login remains completely operational alongside social auth."""
        user = User.objects.create_user(
            username="otp.student@nptor.com",
            email="otp.student@nptor.com",
        )

        with override_settings(
            ALLOWED_HOSTS=["testserver", "localhost"],
            GOOGLE_OAUTH_CLIENT_ID="test-google-client-id.apps.googleusercontent.com",
            GOOGLE_OAUTH_CLIENT_SECRET="test-google-client-secret-123",
            SOCIALACCOUNT_PROVIDERS=self.test_oauth_settings,
        ):
            # Request OTP
            resp = self.client.post(
                reverse("accounts:request-login-otp"),
                {"email": "otp.student@nptor.com"},
            )
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("accounts:verify-login-otp"), resp.url)

            # OTP was created
            otp = EmailOTP.objects.filter(
                user=user,
                purpose=EmailOTP.PURPOSE_LOGIN,
                is_used=False,
            ).first()
            self.assertIsNotNone(otp)
            self.assertTrue(bool(otp.otp_hash))

    def test_google_adapter_id_token_decoding_without_pyjwt(self):
        """
        Verify GoogleOAuth2Adapter decodes id_token cleanly without requiring
        PyJWT to be installed, preventing HTTP 500 in OAuth callback.
        """
        import base64
        import json
        import time
        from unittest.mock import MagicMock
        from allauth.socialaccount.models import SocialApp, SocialToken
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

        client_id = "test-google-client-id.apps.googleusercontent.com"
        app = SocialApp(provider="google", client_id=client_id, secret="secret")

        # Construct valid JWT with claims
        header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode().rstrip("=")
        payload = {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-998877",
            "aud": client_id,
            "email": "fresh.user@example.com",
            "email_verified": True,
            "name": "Fresh User",
            "picture": "https://example.com/avatar.jpg",
            "exp": int(time.time()) + 3600,
        }
        pld = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        dummy_id_token = f"{header}.{pld}.dummy-signature"

        adapter = GoogleOAuth2Adapter(self.rf.get("/"))
        adapter.did_fetch_access_token = True

        # Ensure _decode_id_token decodes without ModuleNotFoundError
        decoded = adapter._decode_id_token(app, dummy_id_token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["email"], "fresh.user@example.com")
        self.assertEqual(decoded["sub"], "google-sub-998877")

        # Test complete_login
        token = SocialToken(token="valid-oauth-access-token", app=app)
        req = self._prepare_request(self.rf.get("/"))
        sociallogin = adapter.complete_login(
            req,
            app,
            token,
            response={"access_token": "valid-oauth-access-token", "id_token": dummy_id_token},
        )
        self.assertIsNotNone(sociallogin)
        self.assertEqual(sociallogin.account.uid, "google-sub-998877")
        self.assertEqual(sociallogin.user.email, "fresh.user@example.com")
        self.assertTrue(sociallogin.email_addresses[0].verified)

    def test_google_adapter_complete_login_fallback_to_userinfo(self):
        """
        When id_token is missing or fails decoding, complete_login seamlessly
        falls back to _fetch_user_info without raising HTTP 500.
        """
        from unittest.mock import MagicMock
        from allauth.socialaccount.models import SocialApp, SocialToken
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

        client_id = "test-google-client-id.apps.googleusercontent.com"
        app = SocialApp(provider="google", client_id=client_id, secret="secret")
        token = SocialToken(token="oauth-token-fallback", app=app)

        adapter = GoogleOAuth2Adapter(self.rf.get("/"))
        adapter._fetch_user_info = MagicMock(return_value={
            "id": "userinfo-id-12345",
            "email": "userinfo.fallback@example.com",
            "verified_email": True,
            "name": "Fallback User",
            "picture": "https://example.com/fallback.jpg",
        })

        req = self._prepare_request(self.rf.get("/"))
        # Pass a corrupted id_token that cannot be decoded
        sociallogin = adapter.complete_login(
            req,
            app,
            token,
            response={"access_token": "oauth-token-fallback", "id_token": "corrupted.token.value"},
        )
        self.assertIsNotNone(sociallogin)
        self.assertEqual(sociallogin.account.uid, "userinfo-id-12345")
        self.assertEqual(sociallogin.user.email, "userinfo.fallback@example.com")
        self.assertTrue(sociallogin.email_addresses[0].verified)
        adapter._fetch_user_info.assert_called_once_with("oauth-token-fallback")

