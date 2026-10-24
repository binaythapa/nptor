from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from accounts.models import UserProfile

User = get_user_model()


class NPTORSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    NPTOR Social Account Adapter.

    Enforces platform security guarantees for third-party social logins:
    1. Keeps the verified Google email address as the NPTOR username.
    2. Requires trusted, verified email identities; blocks unverified social accounts.
    3. Prevents account takeover, inactive user logins, and unauthorized role escalation.
    4. Safely preserves existing user accounts, passwords, exam history, orders,
       subscriptions, and seller permissions upon linking.
    5. Synchronizes email verification state to UserProfile.
    """

    @staticmethod
    def _email_as_username(user):
        email = (getattr(user, "email", "") or "").strip().lower()
        if email:
            user.username = email
            user.email = email

    def pre_social_login(self, request, sociallogin):
        """
        Validate incoming social login identity before processing authentication.
        """
        # 1. Verify that the social provider returned a verified email address
        email_addresses = getattr(sociallogin, "email_addresses", [])
        verified_emails = [
            e.email.strip().lower()
            for e in email_addresses
            if getattr(e, "verified", False) and e.email
        ]

        if not verified_emails:
            messages.error(
                request,
                "Google sign-in requires a verified email address from your Google account.",
            )
            raise ImmediateHttpResponse(redirect("accounts:request-login-otp"))

        primary_email = verified_emails[0]

        # 2. Account connection validation for already authenticated users
        req_user = getattr(request, "user", None)
        if req_user and req_user.is_authenticated:
            if req_user.email and req_user.email.strip().lower() != primary_email:
                messages.error(
                    request,
                    f"Your Google email ({primary_email}) does not match your active NPTOR account ({req_user.email}).",
                )
                raise ImmediateHttpResponse(redirect("accounts:request-login-otp"))

        # 3. Check target user account state if matched or existing
        target_user = getattr(sociallogin, "user", None)
        if target_user and target_user.pk:
            if not target_user.is_active:
                messages.error(
                    request,
                    "This account has been deactivated. Please contact support.",
                )
                raise ImmediateHttpResponse(redirect("accounts:request-login-otp"))

            # Ensure an allauth EmailAddress record exists with verified=True
            # to preserve any existing native password from being wiped
            EmailAddress.objects.get_or_create(
                user=target_user,
                email=primary_email,
                defaults={"verified": True, "primary": True},
            )

            # Update UserProfile email_verified status if not set
            if hasattr(target_user, "profile"):
                profile = target_user.profile
                if not profile.email_verified:
                    profile.email_verified = True
                    profile.save(update_fields=["email_verified"])

    def populate_user(self, request, sociallogin, data):
        """
        Populate new user fields from social provider data.
        Never grant staff or superuser privileges via social attributes.
        """
        user = super().populate_user(request, sociallogin, data)
        self._email_as_username(user)

        # Explicitly enforce least privilege for new accounts
        if not user.pk:
            user.is_staff = False
            user.is_superuser = False

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Save new user created via social signup, initialize unusable password,
        and mark UserProfile email verification.
        """
        user = super().save_user(request, sociallogin, form)
        self._email_as_username(user)

        # Set unusable password for accounts created purely via OAuth
        if not user.has_usable_password():
            user.set_unusable_password()

        user.save(update_fields=["username", "email", "password"])

        # Sync verification state to UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=["email_verified"])

        return user
