from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from accounts.utils.email import send_registration_success_email

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

from accounts.services.cleanup import delete_expired_unverified_users


from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from accounts.services.otp_service import create_registration_otp
from accounts.services.cleanup import delete_expired_unverified_users

User = get_user_model()




from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.shortcuts import render, redirect


def register_view(request):
    """
    Step 1: Create inactive user OR reuse existing inactive user and send OTP
    """

    delete_expired_unverified_users(minutes=30)

    if request.method == "GET":
        return render(request, "accounts/auth/register.html")

    # ----------------------
    # Read form data
    # ----------------------
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password")
    confirm = request.POST.get("confirm_password")

    country = request.POST.get("country") or None
    phone = request.POST.get("phone") or None
    accepted_policy = request.POST.get("accepted_policy")

    # ----------------------
    # Validation
    # ----------------------

    if not first_name or not last_name or not email or not password or not confirm:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Please fill all required fields."},
        )

    if "@" not in email:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Enter a valid email address."},
        )

        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Please fill all required fields."},
        )

    if not accepted_policy:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "You must accept the Terms & Privacy Policy."},
        )

    if password != confirm:
        return render(
            request,
            "accounts/auth/register.html",
            {"error": "Passwords do not match."},
        )

    # ----------------------
    # Check existing user by email
    # ----------------------
    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        if existing_user.is_active:
            return render(
                request,
                "accounts/auth/register.html",
                {"error": "Email already registered."},
            )

        # Resend OTP for unverified user
        create_registration_otp(user=existing_user)
        request.session["registration_user_id"] = existing_user.id
        return redirect("accounts:verify-registration-otp")

    # ----------------------
    # Create inactive user
    # ----------------------
    user = User.objects.create(
        username=email,   # 🔥 EMAIL AS USERNAME
        first_name=first_name.title(),
        last_name=last_name.title(),
        email=email,
        password=make_password(password),
        is_active=False,
    )

    # ----------------------
    # Save profile info
    # ----------------------
    profile = user.profile
    profile.country = country
    profile.phone = phone
    profile.accepted_policy = True
    profile.email_verified = False
    profile.save()

    # ----------------------
    # Send registration OTP
    # ----------------------
    create_registration_otp(user=user)
    request.session["registration_user_id"] = user.id

    return redirect("accounts:verify-registration-otp")


from django.http import JsonResponse
from django.contrib.auth.models import User


from django.http import JsonResponse
from django.contrib.auth.models import User


def check_email_availability(request):
    email = request.GET.get("email", "").strip().lower()

    if not email:
        return JsonResponse({"available": False})

    exists = User.objects.filter(email=email, is_active=True).exists()

    return JsonResponse({
        "available": not exists
    })















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

    # 📧 Send confirmation email
    send_registration_success_email(user=user)

    request.session.pop("registration_user_id", None)

    return redirect("accounts:registration-success")


def registration_success_view(request):
    return render(
        request,
        "accounts/auth/registration_success.html"
    )
