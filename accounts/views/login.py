from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone

from accounts.services.otp_service import create_login_otp
from accounts.models import EmailOTP


@csrf_protect
def request_login_otp_view(request):
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
                if expires_in < 0:
                    expires_in = 0

        return render(
            request,
            "accounts/auth/login.html",
            {
                "expires_in": expires_in,
            },
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

    create_login_otp(user=user)
    request.session["otp_user_id"] = user.id

    return redirect("accounts:verify-login-otp")
