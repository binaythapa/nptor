from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_login_otp_email(*, user, otp_code):
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


from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_registration_success_email(*, user):
    """
    Send confirmation email after successful registration
    """
    subject = "Welcome to Nepal Mentor 🎉"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [user.email]

    html_content = render_to_string(
        "accounts/emails/registration_success.html",
        {
            "user": user,
            "site_name": settings.SITE_NAME,
        },
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=(
            f"Hi {user.username},\n\n"
            "Your account has been successfully created.\n"
            "You can now log in and start learning.\n\n"
            f"— {settings.SITE_NAME}"
        ),
        from_email=from_email,
        to=to,
    )

    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
