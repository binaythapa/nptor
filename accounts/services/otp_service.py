from accounts.models import EmailOTP
from accounts.utils.email import send_login_otp_email


# ============================
# CREATE OTPs
# ============================

def create_login_otp(*, user):
    """
    Create and email OTP for login.
    """
    otp = EmailOTP.create_otp(
        user=user,
        purpose=EmailOTP.PURPOSE_LOGIN,
        ttl_minutes=5,
    )

    send_login_otp_email(
        user=user,
        otp_code=otp.code,
    )

    return otp


def create_password_reset_otp(*, user):
    """
    Create and email OTP for password reset.
    """
    otp = EmailOTP.create_otp(
        user=user,
        purpose=EmailOTP.PURPOSE_PASSWORD_RESET,
        ttl_minutes=10,
    )

    send_login_otp_email(
        user=user,
        otp_code=otp.code,
    )

    return otp


# ============================
# VERIFY OTP (GENERIC)
# ============================

def verify_otp(*, user, code, purpose):
    """
    Verify OTP for a specific purpose (login / password reset).
    """
    try:
        otp = EmailOTP.objects.get(
            user=user,
            code=code,
            purpose=purpose,
            is_used=False,
        )
    except EmailOTP.DoesNotExist:
        return False

    if not otp.is_valid():
        return False

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True
