from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.services.otp_service import (
    create_registration_otp,
    verify_otp,
)
from accounts.models import EmailOTP

User = get_user_model()


from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.services.otp_service import create_registration_otp
from accounts.models import EmailOTP

User = get_user_model()


def register_view(request):
    """
    Step 1: Create inactive user, save profile info & send OTP
    """
    if request.method == "GET":
        return render(request, "accounts/auth/register.html")

    # ----------------------
    # Read form data
    # ----------------------
    username = request.POST.get("username")
    email = request.POST.get("email")
    password = request.POST.get("password")
    confirm = request.POST.get("confirm_password")

    country = request.POST.get("country")
    phone = request.POST.get("phone")
    accepted_policy = request.POST.get("accepted_policy")

    # ----------------------
    # Validation
    # ----------------------
    if not all([username, email, password, confirm, country, phone]):
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "All fields are required"},
        )

    if not accepted_policy:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "You must accept the Terms & Privacy Policy"},
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

    # ----------------------
    # Create inactive user
    # ----------------------
    user = User.objects.create(
        username=username,
        email=email,
        password=make_password(password),
        is_active=False,  # 🔐 activate after OTP verification
    )

    # ----------------------
    # Save profile info
    # ----------------------
    profile = user.profile
    profile.country = country
    profile.phone = phone
    profile.accepted_policy = True
    profile.save(update_fields=["country", "phone", "accepted_policy"])

    # ----------------------
    # Send registration OTP
    # ----------------------
    create_registration_otp(user=user)
    request.session["registration_user_id"] = user.id

    return redirect("accounts:verify-registration-otp")


    create_registration_otp(user=user)
    request.session["registration_user_id"] = user.id

    return redirect("accounts:verify-registration-otp")

from django.utils import timezone
from accounts.models import EmailOTP


def verify_registration_otp_view(request):
    """
    Step 2: Verify REGISTRATION OTP and activate account
    """

    # ======================
    # GET → show OTP page + countdown
    # ======================
    if request.method == "GET":
        user_id = request.session.get("registration_user_id")
        expires_in = None

        if user_id:
            otp = (
                EmailOTP.objects
                .filter(
                    user_id=user_id,
                    purpose=EmailOTP.PURPOSE_REGISTRATION,
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
            "accounts/auth/verify_registration_otp.html",
            {"expires_in": expires_in},
        )

    # ======================
    # POST → verify OTP
    # ======================
    otp_code = request.POST.get("otp")
    user_id = request.session.get("registration_user_id")

    if not otp_code or not user_id:
        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {"error": "Session expired", "expires_in": 0},
        )

    user = User.objects.get(id=user_id)

    if not verify_otp(
        user=user,
        code=otp_code,
        purpose=EmailOTP.PURPOSE_REGISTRATION,
    ):
        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {"error": "Invalid or expired OTP", "expires_in": 0},
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
