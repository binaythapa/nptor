# accounts/views/password_reset.py

from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import EmailOTP

from accounts.services.otp_service import (
    create_password_reset_otp,
    verify_otp,
)


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()


# ============================================================
# PASSWORD RESET - REQUEST OTP
# ============================================================

def request_password_reset_otp_view(request):
    """
    Step 1:
    Request a password-reset OTP.

    For security, the response does not reveal whether
    the supplied email address exists.
    """

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "accounts/auth/password_reset_request.html",
        )


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    email = (
        request.POST.get(
            "email",
            "",
        )
        .strip()
        .lower()
    )


    # --------------------------------------------------------
    # VALIDATE EMAIL
    # --------------------------------------------------------

    if not email:

        return render(
            request,
            "accounts/auth/password_reset_request.html",
            {
                "error": "Email is required.",
            },
        )


    # --------------------------------------------------------
    # FIND ACTIVE USER
    #
    # Do not reveal whether the account exists.
    # --------------------------------------------------------

    user = (
        User.objects
        .filter(
            email__iexact=email,
            is_active=True,
        )
        .order_by("id")
        .first()
    )


    # --------------------------------------------------------
    # USER NOT FOUND
    #
    # Same user-facing behavior regardless of whether
    # the email exists.
    # --------------------------------------------------------

    if not user:

        return render(
            request,
            "accounts/auth/password_reset_request.html",
            {
                "message": (
                    "If an account exists with this email, "
                    "you will receive a password reset OTP."
                ),
            },
        )


    # --------------------------------------------------------
    # CREATE PASSWORD RESET OTP
    # --------------------------------------------------------

    create_password_reset_otp(
        user=user
    )


    # --------------------------------------------------------
    # STORE USER IN SESSION
    # --------------------------------------------------------

    request.session[
        "pwd_reset_user_id"
    ] = user.id


    # --------------------------------------------------------
    # REDIRECT TO OTP VERIFICATION
    # --------------------------------------------------------

    return redirect(
        "accounts:password-reset-verify"
    )


# ============================================================
# PASSWORD RESET - VERIFY OTP
# ============================================================

def verify_password_reset_otp_view(request):
    """
    Step 2:
    Verify password-reset OTP and set the new password.
    """

    # --------------------------------------------------------
    # GET USER FROM SESSION
    # --------------------------------------------------------

    user_id = request.session.get(
        "pwd_reset_user_id"
    )


    if not user_id:

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "Session expired.",
            },
        )


    # --------------------------------------------------------
    # LOAD USER
    # --------------------------------------------------------

    try:

        user = User.objects.get(
            id=user_id
        )

    except User.DoesNotExist:

        request.session.pop(
            "pwd_reset_user_id",
            None,
        )

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "Invalid session.",
            },
        )


    # --------------------------------------------------------
    # GET LATEST UNUSED PASSWORD RESET OTP
    # --------------------------------------------------------

    otp_obj = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=(
                EmailOTP.PURPOSE_PASSWORD_RESET
            ),
            is_used=False,
        )
        .order_by(
            "-created_at"
        )
        .first()
    )


    if not otp_obj:

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "OTP session expired.",
                "expires_in": 0,
            },
        )


    # --------------------------------------------------------
    # CALCULATE REMAINING TIME
    # --------------------------------------------------------

    expires_in = int(
        (
            otp_obj.expires_at
            - timezone.now()
        ).total_seconds()
    )

    expires_in = max(
        expires_in,
        0,
    )


    # --------------------------------------------------------
    # GET
    #
    # Display OTP + new password form.
    # --------------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "expires_in": expires_in,
            },
        )


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    otp_code = (
        request.POST.get(
            "otp",
            "",
        )
        .strip()
    )

    password = request.POST.get(
        "password",
        "",
    )

    confirm_password = request.POST.get(
        "confirm_password",
        "",
    )


    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if (
        not otp_code
        or not password
        or not confirm_password
    ):

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "All fields are required.",
                "expires_in": expires_in,
            },
        )


    # --------------------------------------------------------
    # PASSWORD MATCH
    # --------------------------------------------------------

    if password != confirm_password:

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "Passwords do not match.",
                "expires_in": expires_in,
            },
        )


    # --------------------------------------------------------
    # SERVER-SIDE EXPIRATION CHECK
    # --------------------------------------------------------

    if expires_in <= 0:

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "OTP has expired.",
                "expires_in": 0,
            },
        )


    # --------------------------------------------------------
    # VERIFY OTP
    #
    # verify_otp() uses EmailOTP.otp_hash and
    # EmailOTP.verify().
    # --------------------------------------------------------

    is_valid = verify_otp(
        user=user,
        code=otp_code,
        purpose=(
            EmailOTP.PURPOSE_PASSWORD_RESET
        ),
    )


    if not is_valid:

        return render(
            request,
            "accounts/auth/password_reset_verify.html",
            {
                "error": "Invalid or expired OTP.",
                "expires_in": expires_in,
            },
        )


    # --------------------------------------------------------
    # UPDATE PASSWORD
    #
    # set_password() automatically uses Django's configured
    # password hasher.
    # --------------------------------------------------------

    user.set_password(
        password
    )

    user.save(
        update_fields=[
            "password",
        ]
    )


    # --------------------------------------------------------
    # CLEAR PASSWORD RESET SESSION
    # --------------------------------------------------------

    request.session.pop(
        "pwd_reset_user_id",
        None,
    )


    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return redirect(
        "accounts:password-reset-success"
    )


# ============================================================
# PASSWORD RESET SUCCESS
# ============================================================

def password_reset_success_view(request):
    """
    Password reset success page.
    """

    return render(
        request,
        "accounts/auth/password_reset_success.html",
    )