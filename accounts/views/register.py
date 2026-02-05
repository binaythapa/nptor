from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.services.otp_service import (
    create_registration_otp,
    verify_otp,
)
from accounts.models import EmailOTP

User = get_user_model()


def register_view(request):
    """
    Step 1: Create inactive user & send OTP
    """
    if request.method == "GET":
        return render(request, "accounts/auth/register.html")

    username = request.POST.get("username")
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirm = request.POST.get("confirm_password")

    if not all([username, email, password, confirm]):
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "All fields are required"},
        )

    if password != confirm:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Passwords do not match"},
        )

    if User.objects.filter(username=username).exists():
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Username already taken"},
        )

    if User.objects.filter(email=email).exists():
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Email already registered"},
        )

    user = User.objects.create(
        username=username,
        email=email,
        password=make_password(password),
        is_active=False,   # 🔐 IMPORTANT
    )

    create_registration_otp(user=user)
    request.session["registration_user_id"] = user.id

    return redirect("accounts:verify-registration-otp")


def verify_registration_otp_view(request):
    """
    Step 2: Verify OTP and activate account
    """
    if request.method == "GET":
        return render(request, "accounts/auth/verify_registration_otp.html")

    otp = request.POST.get("otp")
    user_id = request.session.get("registration_user_id")

    if not otp or not user_id:
        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {"error": "Session expired"},
        )

    user = User.objects.get(id=user_id)

    if not verify_otp(
        user=user,
        code=otp,
        purpose=EmailOTP.PURPOSE_REGISTRATION,
    ):
        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {"error": "Invalid or expired OTP"},
        )

    user.is_active = True
    user.save(update_fields=["is_active"])

    request.session.pop("registration_user_id", None)

    return redirect("accounts:registration-success")


def registration_success_view(request):
    return render(
        request,
        "accounts/auth/registration_success.html"
    )
