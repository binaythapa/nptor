from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_login_otp_email(*, user, otp_code):
    """
    Sends branded HTML OTP email for login.
    """
    subject = "Your Login OTP"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [user.email]

    html_content = render_to_string(
        "accounts/emails/login_otp.html",
        {
            "user": user,
            "otp": otp_code,
            "site_name": settings.SITE_NAME,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body="Your OTP is: " + otp_code,
        from_email=from_email,
        to=to,
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
