from accounts.models import EmailOTP
from accounts.utils.email import send_login_otp_email


def create_login_otp(*, user):
    """
    Create OTP and send login email.
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


def verify_login_otp(*, user, code):
    """
    Verify OTP for login.
    """
    try:
        otp = EmailOTP.objects.get(
            user=user,
            code=code,
            purpose=EmailOTP.PURPOSE_LOGIN,
            is_used=False,
        )
    except EmailOTP.DoesNotExist:
        return False

    if not otp.is_valid():
        return False

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True
