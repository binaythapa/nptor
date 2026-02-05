from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, get_user_model

from accounts.services.otp_service import verify_login_otp
from accounts.models.security import AccountLock

User = get_user_model()


def verify_login_otp_view(request):
    if request.method == "GET":
        return render(request, "accounts/auth/verify_otp.html")

    otp_code = request.POST.get("otp")
    user_id = request.session.get("otp_user_id")

    if not otp_code or not user_id:
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "OTP session expired"},
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

    if not verify_login_otp(user=user, code=otp_code):
        lock.register_failure()
        return render(
            request,
            "accounts/auth/verify_otp.html",
            {"error": "Invalid or expired OTP"},
        )

    # 🔑 login with explicit backend
    login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )

    lock.reset()
    request.session.pop("otp_user_id", None)

    # ✅ redirect user
    return redirect("quiz:dashboard")
