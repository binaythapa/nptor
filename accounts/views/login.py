from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone

from accounts.services.otp_service import create_login_otp
from accounts.models import EmailOTP

import logging
from core.utils.memory import get_memory_usage_mb

logger = logging.getLogger("django")


@csrf_protect
def request_login_otp_view(request):
    # ---- lightweight memory telemetry ----
   
    mem = get_memory_usage_mb()
    if mem is not None:
        logger.info(f"Login OTP view memory usage: {mem} MB")

    """
    Step 1: Username + password → send OTP
    """

    # ======================
    # GET → show login form (+ countdown if OTP exists)
    # ======================
    if request.method == "GET":
        user_id = request.session.get("otp_user_id")
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
                    (otp.expires_at - timezone.now()).total_seconds()
                )
                expires_in = max(expires_in, 0)

        return render(
            request,
            "accounts/auth/login.html",
            {"expires_in": expires_in},
        )

    # ======================
    # POST → validate credentials & create OTP
    # ======================
    username = request.POST.get("username")
    password = request.POST.get("password")

    if not username or not password:
        return render(
            request,
            "accounts/auth/login.html",
            {"error": "Username and password required"},
        )

    user = authenticate(request, username=username, password=password)

    if not user:
        return render(
            request,
            "accounts/auth/login.html",
            {"error": "Invalid credentials"},
        )

    if not user.email:
        return render(
            request,
            "accounts/auth/login.html",
            {"error": "No email associated with this account"},
        )

    # ---- OTP cooldown (prevents abuse & load) ----
    recent_otp = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=EmailOTP.PURPOSE_LOGIN,
            is_used=False,
            created_at__gte=timezone.now() - timezone.timedelta(seconds=30),
        )
        .exists()
    )

    if recent_otp:
        return render(
            request,
            "accounts/auth/login.html",
            {"error": "Please wait before requesting another OTP"},
        )

    # ---- create OTP (async sending inside service) ----
    create_login_otp(user=user)
    request.session["otp_user_id"] = user.id

    return redirect("accounts:verify-login-otp")
