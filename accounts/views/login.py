# accounts/views/login.py

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from accounts.models import EmailOTP
from accounts.services.otp_service import create_login_otp

from core.utils.memory import get_memory_usage_mb


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger("django")


# ============================================================
# LOGIN - REQUEST OTP
# ============================================================

@csrf_protect
def request_login_otp_view(request):
    """
    Step 1 of login:

        Email
          ↓
        Find active user
          ↓
        Create OTP
          ↓
        Send OTP email
          ↓
        Store user ID in session
          ↓
        Redirect to OTP verification
    """

    # --------------------------------------------------------
    # MEMORY TELEMETRY
    # --------------------------------------------------------

    mem = get_memory_usage_mb()

    if mem is not None:
        logger.info(
            "Login OTP view memory usage: %s MB",
            mem,
        )

    # --------------------------------------------------------
    # GET
    #
    # Show login page.
    # If an OTP already exists, show remaining time.
    # --------------------------------------------------------

    if request.method == "GET":

        user_id = request.session.get(
            "otp_user_id"
        )

        expires_in = None

        if user_id:

            otp = (
                EmailOTP.objects
                .filter(
                    user_id=user_id,
                    purpose=EmailOTP.PURPOSE_LOGIN,
                    is_used=False,
                )
                .order_by("-created_at")
                .first()
            )

            if otp and otp.expires_at:

                expires_in = int(
                    (
                        otp.expires_at
                        - timezone.now()
                    ).total_seconds()
                )

                expires_in = max(
                    expires_in,
                    0,
                )

        return render(
            request,
            "accounts/auth/login.html",
            {
                "expires_in": expires_in,
            },
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    email = (
        request.POST.get(
            "email",
            "",
        )
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # VALIDATE EMAIL
    # --------------------------------------------------------

    if not email:

        return render(
            request,
            "accounts/auth/login.html",
            {
                "error": "Email address is required.",
            },
        )

    # --------------------------------------------------------
    # FIND ACTIVE USER
    #
    # We deliberately don't reveal whether the email exists.
    # --------------------------------------------------------

    user = (
        User.objects
        .filter(
            email__iexact=email,
            is_active=True,
        )
        .order_by("id")
        .first()
    )

    if not user:

        return render(
            request,
            "accounts/auth/login.html",
            {
                "message": (
                    "If an account exists with this email, "
                    "a login OTP will be sent."
                ),
            },
        )

    # --------------------------------------------------------
    # EMAIL REQUIRED
    # --------------------------------------------------------

    if not user.email:

        return render(
            request,
            "accounts/auth/login.html",
            {
                "message": (
                    "If an account exists with this email, "
                    "a login OTP will be sent."
                ),
            },
        )

    # --------------------------------------------------------
    # OTP COOLDOWN
    #
    # Prevent multiple OTP requests within 30 seconds.
    # --------------------------------------------------------

    cooldown_since = (
        timezone.now()
        - timedelta(seconds=30)
    )

    recent_otp = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=EmailOTP.PURPOSE_LOGIN,
            is_used=False,
            created_at__gte=cooldown_since,
        )
        .exists()
    )

    if recent_otp:

        return render(
            request,
            "accounts/auth/login.html",
            {
                "error": (
                    "Please wait 30 seconds before "
                    "requesting another OTP."
                ),
            },
        )

    # --------------------------------------------------------
    # CREATE LOGIN OTP
    # --------------------------------------------------------

    create_login_otp(
        user=user
    )

    # --------------------------------------------------------
    # STORE USER IN SESSION
    # --------------------------------------------------------

    request.session[
        "otp_user_id"
    ] = user.id

    # --------------------------------------------------------
    # REDIRECT TO OTP VERIFICATION
    # --------------------------------------------------------

    return redirect(
        "accounts:verify-login-otp"
    )