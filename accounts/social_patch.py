"""
NPTOR Google Social Auth Resilience Patch.

Ensures Google OAuth complete_login can decode and verify ID tokens without
hard-failing when PyJWT is not installed, leveraging the existing `google-auth`
and `cryptography` packages, or gracefully falling back to Google's verified
userinfo endpoint over TLS.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_PATCHED = False


def patch_google_adapter() -> None:
    """
    Idempotently monkey-patches GoogleOAuth2Adapter and jwtkit.verify_and_decode
    to provide robust fallback ID token decoding and user info fetching.
    """
    global _PATCHED
    if _PATCHED:
        return

    try:
        from allauth.socialaccount.internal import jwtkit
        from allauth.socialaccount.providers.google.views import (
            GoogleOAuth2Adapter,
            _verify_and_decode as orig_google_verify_and_decode,
        )
        from allauth.socialaccount.providers.oauth2.client import OAuth2Error
    except ImportError:
        logger.warning("django-allauth Google provider not available to patch.")
        return

    orig_jwtkit_verify = jwtkit.verify_and_decode

    def safe_jwtkit_verify_and_decode(*args, **kwargs):
        try:
            return orig_jwtkit_verify(*args, **kwargs)
        except ModuleNotFoundError as exc:
            if "jwt" not in str(exc):
                raise
            # PyJWT is not installed; handle using google.auth
            credential = kwargs.get("credential")
            verify_signature = kwargs.get("verify_signature", True)
            audience = kwargs.get("audience")
            issuer = kwargs.get("issuer")

            if not verify_signature:
                payload = None
                try:
                    from google.auth import jwt as google_jwt

                    payload = google_jwt.decode(credential, verify=False)
                except Exception:
                    pass

                if payload is None:
                    import base64
                    import json

                    parts = str(credential).split(".")
                    if len(parts) >= 2:
                        p_b64 = parts[1]
                        rem = len(p_b64) % 4
                        if rem:
                            p_b64 += "=" * (4 - rem)
                        payload = json.loads(base64.urlsafe_b64decode(p_b64).decode("utf-8"))

                if payload:
                    if audience and payload.get("aud") != audience:
                        raise OAuth2Error(f"Invalid audience: {payload.get('aud')}")
                    if issuer and payload.get("iss") not in (issuer, issuer.rstrip("/")):
                        raise OAuth2Error(f"Invalid issuer: {payload.get('iss')}")
                    exp = payload.get("exp")
                    if exp and exp < time.time() - 300:
                        raise OAuth2Error("ID token expired")
                    return payload
                raise OAuth2Error("Unable to decode ID token payload")

            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            return google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), audience=audience
            )

    jwtkit.verify_and_decode = safe_jwtkit_verify_and_decode

    def safe_decode_id_token(self, app, id_token):
        verify_signature = not getattr(self, "did_fetch_access_token", False)
        try:
            return safe_jwtkit_verify_and_decode(
                credential=id_token,
                keys_url=getattr(self, "CERTS_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                issuer=getattr(self, "id_token_issuer", "https://accounts.google.com"),
                audience=getattr(app, "client_id", ""),
                lookup_kid=jwtkit.lookup_kid_pem_x509_certificate,
                verify_signature=verify_signature,
            )
        except Exception as exc:
            logger.warning("ID token decoding failed: %s; falling back to userinfo", exc)
            return None

    GoogleOAuth2Adapter._decode_id_token = safe_decode_id_token

    def safe_complete_login(self, request, app, token, **kwargs):
        response = kwargs.get("response", {})
        id_token = response.get("id_token")
        data = None

        if id_token:
            try:
                data = self._decode_id_token(app, id_token)
            except Exception as exc:
                logger.warning("complete_login: _decode_id_token raised %s", exc)
                data = None

            if data and self.fetch_userinfo and "picture" not in data:
                try:
                    info = self._fetch_user_info(token.token)
                    picture = info.get("picture")
                    if picture:
                        data["picture"] = picture
                except Exception:
                    pass

        # If data is missing (either no id_token or id_token decode failed/returned None),
        # query Google's userinfo endpoint directly using the valid access token
        if not data:
            data = self._fetch_user_info(token.token)

        login = self.get_provider().sociallogin_from_response(request, data)
        return login

    GoogleOAuth2Adapter.complete_login = safe_complete_login
    _PATCHED = True
