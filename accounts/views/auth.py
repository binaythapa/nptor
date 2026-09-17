# accounts/views/auth.py

from django.contrib.auth import get_user_model, login
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from accounts.models import EmailOTP
from accounts.models.security import AccountLock

from accounts.services.otp_service import verify_otp


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()


# ============================================================
# LOGIN OTP VERIFICATION
# ============================================================

@csrf_protect
def verify_login_otp_view(request):
    """
    Step 2 of login:

        Email
          ↓
        OTP generated
          ↓
        OTP verification
          ↓
        Account lock check
          ↓
        Django login
          ↓
        Role-based dashboard
    """

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
                expires_in = max(
                    int((otp.expires_at - timezone.now()).total_seconds()),
                    0,
                )

        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"expires_in": expires_in},
        )

    otp_code = request.POST.get("otp", "").strip()
    user_id = request.session.get("otp_user_id")

    if not otp_code or not user_id:
        request.session.pop("otp_user_id", None)
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "OTP session expired.", "expires_in": 0},
        )

    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        request.session.pop("otp_user_id", None)
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "Invalid login session.", "expires_in": 0},
        )

    lock, _ = AccountLock.objects.get_or_create(user=user)

    if lock.is_locked():
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {
                "error": "Your account is temporarily locked.",
                "expires_in": 0,
            },
        )

    otp_obj = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=EmailOTP.PURPOSE_LOGIN,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    expires_in = 0
    if otp_obj and otp_obj.expires_at:
        expires_in = max(
            int((otp_obj.expires_at - timezone.now()).total_seconds()),
            0,
        )

    if not otp_obj or expires_in <= 0:
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "OTP has expired.", "expires_in": 0},
        )

    is_valid = verify_otp(
        user=user,
        code=otp_code,
        purpose=EmailOTP.PURPOSE_LOGIN,
    )

    if not is_valid:
        lock.register_failure()
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {
                "error": "Invalid or expired OTP.",
                "expires_in": expires_in,
            },
        )

    lock.reset()
    login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    request.session.pop("otp_user_id", None)

    # Platform administrators use the platform administration dashboard.
    if user.is_staff or user.is_superuser:
        return redirect("quiz:admin_dashboard")

    return redirect("quiz:student_dashboard")
