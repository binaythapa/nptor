from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.services.otp_service import (
    create_password_reset_otp,
    verify_otp,
)
from accounts.models import EmailOTP

User = get_user_model()


def request_password_reset_otp_view(request):
    """
    Step 1: Request OTP for password reset
    """
    if request.method == "GET":
        return render(request, "accounts/auth/password_reset_request.html")

    email = request.POST.get("email")

    if not email:
        return render(
            request,
            "accounts/auth/password_reset_request.html",
            {"error": "Email is required"},
        )

    user = (
        User.objects
        .filter(email=email, is_active=True)
        .order_by("id")
        .first()
    )

    # 🔐 Security: do NOT reveal whether email exists
    if not user:
        return render(
            request,
            "accounts/auth/password_reset_request.html",
            {
                "message": (
                    "If an account exists with this email, "
                    "you will receive a password reset OTP."
                )
            },
        )

    create_password_reset_otp(user=user)
    request.session["pwd_reset_user_id"] = user.id

    return redirect("accounts:password-reset-verify")


def verify_password_reset_otp_view(request):
    """
    Step 2: Verify PASSWORD RESET OTP and set new password
    """
    if request.method == "GET":
        return render(request, "accounts/auth/password_reset_verify.html")

    otp = request.POST.get("otp")
    password = request.POST.get("password")
    confirm = request.POST.get("confirm_password")

    user_id = request.session.get("pwd_reset_user_id")

    if not user_id:
        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {"error": "Session expired"},
        )

    if not otp or not password or not confirm:
        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {"error": "All fields are required"},
        )

    if password != confirm:
        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {"error": "Passwords do not match"},
        )

    user = User.objects.get(id=user_id)

    # ✅ FIX: verify OTP with PASSWORD_RESET purpose
    if not verify_otp(
        user=user,
        code=otp,
        purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
    ):
        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {"error": "Invalid or expired OTP"},
        )

    user.password = make_password(password)
    user.save(update_fields=["password"])

    request.session.pop("pwd_reset_user_id", None)

    return redirect("accounts:password-reset-success")



def password_reset_success_view(request):
    """
    Password reset success page
    """
    return render(
        request,
        "accounts/auth/password_reset_success.html"
    )

