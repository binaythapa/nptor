from django.conf import settings


def social_login_config(request):
    """Expose whether Google OAuth has been configured."""
    return {
        "google_oauth_enabled": bool(
            settings.GOOGLE_OAUTH_CLIENT_ID
            and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ),
    }
