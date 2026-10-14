from accounts.models import EmailOTP

from accounts.services.email_service import (
    send_login_otp_email,
    send_registration_otp_email,
    send_password_reset_otp_email,
)


# ============================================================
# LOGIN OTP
# ============================================================

def create_login_otp(*, user):
    """
    Create and email a login OTP.

    Valid for 5 minutes.
    """

    otp, code = EmailOTP.create_otp(
        email=user.email,
        user=user,
        purpose=EmailOTP.PURPOSE_LOGIN,
        ttl_minutes=5,
    )

    send_login_otp_email(
        user=user,
        otp_code=code,
    )

    return otp


# ============================================================
# PASSWORD RESET OTP
# ============================================================

def create_password_reset_otp(*, user):
    """
    Create and email a password reset OTP.

    Valid for 10 minutes.
    """

    otp, code = EmailOTP.create_otp(
        email=user.email,
        user=user,
        purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
        ttl_minutes=10,
    )

    send_password_reset_otp_email(
        user=user,
        otp_code=code,
    )

    return otp


# ============================================================
# REGISTRATION OTP
# ============================================================

def create_registration_otp(*, user):
    """
    Create and email a registration verification OTP.

    Valid for 10 minutes.
    """

    otp, code = EmailOTP.create_otp(
        email=user.email,
        user=user,
        purpose=EmailOTP.PURPOSE_REGISTRATION,
        ttl_minutes=10,
    )

    send_registration_otp_email(
        user=user,
        otp_code=code,
    )

    return otp


# ============================================================
# VERIFY OTP
# ============================================================

def verify_otp(
    *,
    user,
    code,
    purpose,
):
    """
    Verify the latest unused OTP for a user and purpose.

    Returns:
        True  -> OTP successfully verified
        False -> OTP invalid/expired/used/locked
    """

    if not user:
        return False

    if not code:
        return False

    otp = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=purpose,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    if not otp:
        return False

    return otp.verify(code)