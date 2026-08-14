# accounts/utils/email.py

"""
Backward-compatible email helpers.

Email delivery is now implemented in:
    accounts.services.email_service

These wrappers are retained so existing imports do not
immediately break.
"""

from accounts.services.email_service import (
    send_login_otp_email,
    send_registration_success_email,
)

__all__ = [
    "send_login_otp_email",
    "send_registration_success_email",
]