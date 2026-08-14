from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# ============================================================
# COMMON HTML EMAIL SENDER
# ============================================================

def _send_html_email(
    *,
    subject,
    template,
    context,
    to,
):
    """
    Common HTML email sender.

    Raises an exception if email delivery fails.
    """

    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string(
        template,
        context,
    )

    text_content = (
        f"{subject}\n\n"
        f"Please open this email in an HTML-compatible "
        f"email client."
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to,
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send(
        fail_silently=False
    )


# ============================================================
# GENERIC OTP EMAIL
# ============================================================

def send_otp_email(
    *,
    user,
    otp_code,
    ttl_minutes,
    subject,
):
    """
    Send a generic OTP email.

    Used for:
        - Login
        - Registration verification
        - Password reset
    """

    _send_html_email(
        subject=subject,
        template="accounts/emails/otp_email.html",
        context={
            "user": user,
            "otp": otp_code,
            "ttl": ttl_minutes,
            "year": datetime.now().year,
            "site_name": settings.SITE_NAME,
        },
        to=[user.email],
    )


# ============================================================
# LOGIN OTP
# ============================================================

def send_login_otp_email(
    *,
    user,
    otp_code,
):
    """
    Send login OTP.
    """

    send_otp_email(
        user=user,
        otp_code=otp_code,
        ttl_minutes=5,
        subject="Your Login OTP",
    )


# ============================================================
# REGISTRATION OTP
# ============================================================

def send_registration_otp_email(
    *,
    user,
    otp_code,
):
    """
    Send registration/email verification OTP.
    """

    send_otp_email(
        user=user,
        otp_code=otp_code,
        ttl_minutes=10,
        subject="Verify Your Email",
    )


# ============================================================
# PASSWORD RESET OTP
# ============================================================

def send_password_reset_otp_email(
    *,
    user,
    otp_code,
):
    """
    Send password reset OTP.
    """

    send_otp_email(
        user=user,
        otp_code=otp_code,
        ttl_minutes=10,
        subject="Password Reset OTP",
    )


# ============================================================
# REGISTRATION SUCCESS
# ============================================================

def send_registration_success_email(
    *,
    user,
):
    """
    Send registration confirmation email.
    """

    _send_html_email(
        subject="Welcome to Nepal Mentor 🎉",
        template="accounts/emails/registration_success.html",
        context={
            "user": user,
            "site_name": settings.SITE_NAME,
        },
        to=[user.email],
    )