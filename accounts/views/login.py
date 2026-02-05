from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_protect

from accounts.services.otp_service import create_login_otp


@csrf_protect
def request_login_otp_view(request):
    """
    Step 1: Username + password → send OTP
    """
    if request.method == "GET":
        return render(request, "accounts/auth/login.html")

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
