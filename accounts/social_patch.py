"""
NPTOR Google Social Auth Security & Resilience Patch.

Enforces strict OpenID Connect and OAuth 2.0 security validations:
1. Cryptographic RSA signature verification against Google's public certificates.
2. Strict issuer ('accounts.google.com' / 'https://accounts.google.com') and audience validation.
3. Expiration and clock-skew enforcement.
4. Nonce validation when present.
5. Never accepts an ID token based solely on unverified decoded claims.
6. Authenticated userinfo fallback over HTTPS validating stable subject identifier (sub/id)
   and verified-email status.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_PATCHED = False


def patch_google_adapter() -> None:
    """
    Idempotently patches GoogleOAuth2Adapter and jwtkit.verify_and_decode
    to enforce strict cryptographic signature verification and secure userinfo fallback.
    """
    global _PATCHED
    if _PATCHED:
        return

    try:
        from allauth.socialaccount.internal import jwtkit
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
        from allauth.socialaccount.providers.oauth2.client import OAuth2Error
    except ImportError:
        logger.warning("django-allauth Google provider not available to patch.")
        return

    orig_jwtkit_verify = jwtkit.verify_and_decode

    def secure_verify_and_decode(credential, audience=None, **kwargs):
        """
        Cryptographically verifies and decodes Google ID tokens using
        google.oauth2.id_token and Google's public certificate endpoints.
        Strictly enforces signature, issuer, audience, and expiry.
        """
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            # verify_oauth2_token validates:
            # - RSA signature against Google public certs
            # - Issuer is accounts.google.com or https://accounts.google.com
            # - Audience matches audience (client_id)
            # - Token has not expired (exp and iat)
            request = google_requests.Request()
            payload = google_id_token.verify_oauth2_token(
                credential,
                request,
                audience=audience,
            )
            return payload
        except Exception as exc:
            # Also try default allauth jwtkit if PyJWT is available
            try:
                return orig_jwtkit_verify(credential=credential, audience=audience, **kwargs)
            except Exception:
                pass
            logger.warning("Cryptographic ID token verification failed: %s", exc)
            raise OAuth2Error(f"ID token verification failed: {exc}") from exc

    jwtkit.verify_and_decode = secure_verify_and_decode

    def secure_decode_id_token(self, app, id_token):
        """
        Strictly decodes and cryptographically validates the ID token.
        Never accepts unverified claims.
        """
        client_id = getattr(app, "client_id", "")
        return secure_verify_and_decode(
            credential=id_token,
            keys_url=getattr(self, "CERTS_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            issuer=getattr(self, "id_token_issuer", "https://accounts.google.com"),
            audience=client_id,
            lookup_kid=jwtkit.lookup_kid_pem_x509_certificate,
            verify_signature=True,
        )

    GoogleOAuth2Adapter._decode_id_token = secure_decode_id_token

    def secure_complete_login(self, request, app, token, **kwargs):
        """
        Completes Google OAuth login with strict security safeguards:
        1. If id_token is provided, cryptographically verify it (signature, iss, aud, exp, nonce).
        2. If id_token verification fails or is absent, fallback to Google's HTTPS userinfo
           endpoint using the authenticated access token.
        3. Validate stable subject identifier (sub/id), presence of email, and verified email status.
        """
        response = kwargs.get("response", {})
        id_token = response.get("id_token")
        data = None

        if id_token:
            try:
                data = self._decode_id_token(app, id_token)

                # Validate nonce if session recorded one
                session = getattr(request, "session", None)
                if session:
                    state_data = session.get("socialaccount_state", {})
                    expected_nonce = state_data.get("nonce") if isinstance(state_data, dict) else None
                    if expected_nonce and data.get("nonce") != expected_nonce:
                        raise OAuth2Error("ID token nonce mismatch")

                if self.fetch_userinfo and "picture" not in data:
                    try:
                        info = self._fetch_user_info(token.token)
                        picture = info.get("picture")
                        if picture:
                            data["picture"] = picture
                    except Exception:
                        pass
            except OAuth2Error:
                raise
            except Exception as exc:
                logger.warning("ID token verification error: %s; falling back to HTTPS userinfo", exc)
                data = None

        # Authenticated userinfo fallback over TLS
        if not data:
            data = self._fetch_user_info(token.token)

        # Validate subject identifier, email, and email verification status
        sub = data.get("sub") or data.get("id")
        if not sub or not str(sub).strip():
            raise OAuth2Error("Missing stable Google subject identifier")

        email = (data.get("email") or "").strip()
        if not email:
            raise OAuth2Error("Missing email from Google profile")

        email_verified = bool(data.get("email_verified") or data.get("verified_email"))
        if not email_verified:
            raise OAuth2Error("Unverified email address from Google account")

        login = self.get_provider().sociallogin_from_response(request, data)
        return login

    GoogleOAuth2Adapter.complete_login = secure_complete_login
    _PATCHED = True
