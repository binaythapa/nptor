from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.utils import timezone

from accounts.services.otp_service import verify_otp
from accounts.models import EmailOTP
from accounts.models.security import AccountLock

User = get_user_model()


def verify_login_otp_view(request):
    """
    Step 2: Verify LOGIN OTP and log user in
    """

    # ======================
    # GET → show OTP page + countdown
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
            "accounts/auth/verify_otp.html",
            {
                "expires_in": expires_in,
            },
        )

    # ======================
    # POST → verify OTP
    # ======================
    otp_code = request.POST.get("otp")
    user_id = request.session.get("otp_user_id")

    if not otp_code or not user_id:
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {
                "error": "OTP session expired",
                "expires_in": 0,
            },
        )

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "Invalid session"},
        )

    lock, _ = AccountLock.objects.get_or_create(user=user)

    if lock.is_locked():
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "Account locked"},
        )

    # ✅ Verify OTP (LOGIN purpose)
    if not verify_otp(
        user=user,
        code=otp_code,
        purpose=EmailOTP.PURPOSE_LOGIN,
    ):
        lock.register_failure()
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {
                "error": "Invalid or expired OTP",
                "expires_in": 0,
            },
        )

    # ======================
    # SUCCESS
    # ======================
    lock.reset()

    login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )

    request.session.pop("otp_user_id", None)

    return redirect("quiz:dashboard")
