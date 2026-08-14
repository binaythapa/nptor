"""
accounts/services/auth_service.py

Central Authentication Service

Responsibilities
----------------
✓ Create User
✓ Create Client Profile
✓ Link Social Accounts
✓ Update Social Accounts
✓ Find User
✓ Generate Username
✓ Passwordless Accounts
✓ Login
✓ Logout
"""

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import Client, SocialAccount


class AuthService:

    # ==========================================================
    # USER LOOKUP
    # ==========================================================

    @staticmethod
    def get_user_by_email(email: str):
        if not email:
            return None

        return User.objects.filter(
            email=email.strip().lower()
        ).first()

    @staticmethod
    def get_user_by_username(username: str):
        return User.objects.filter(
            username=username
        ).first()

    # ==========================================================
    # USERNAME GENERATOR
    # ==========================================================

    @staticmethod
    def generate_username(email: str):

        base = email.split("@")[0].lower()

        username = base

        counter = 1

        while User.objects.filter(username=username).exists():

            username = f"{base}{counter}"

            counter += 1

        return username

    # ==========================================================
    # CREATE CLIENT
    # ==========================================================

    @staticmethod
    def create_client(user):

        client, _ = Client.objects.get_or_create(
            user=user
        )

        return client

    # ==========================================================
    # CREATE USER
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def create_user(
        email,
        first_name="",
        last_name="",
        username=None,
        provider="email",
        provider_id=None,
        profile_picture=None,
        email_verified=False,
        raw_data=None,
    ):
        """
        Creates a new user.

        Returns

            user,
            created
        """

        email = email.strip().lower()

        existing = AuthService.get_user_by_email(email)

        if existing:

            AuthService.create_client(existing)

            if provider != "email":

                AuthService.link_social_account(
                    user=existing,
                    provider=provider,
                    provider_id=provider_id,
                    profile_picture=profile_picture,
                    email_verified=email_verified,
                    raw_data=raw_data,
                )

            return existing, False

        if not username:

            username = AuthService.generate_username(email)

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        # Passwordless Authentication
        user.set_unusable_password()

        user.save()

        AuthService.create_client(user)

        if provider != "email":

            AuthService.link_social_account(
                user=user,
                provider=provider,
                provider_id=provider_id,
                profile_picture=profile_picture,
                email_verified=email_verified,
                raw_data=raw_data,
            )

        return user, True

    # ==========================================================
    # LINK SOCIAL ACCOUNT
    # ==========================================================

    @staticmethod
    @transaction.atomic
    def link_social_account(
        user,
        provider,
        provider_id,
        profile_picture=None,
        email_verified=True,
        raw_data=None,
    ):

        social, created = SocialAccount.objects.get_or_create(

            provider=provider,

            provider_id=provider_id,

            defaults={

                "user": user,

                "email": user.email,

                "full_name": f"{user.first_name} {user.last_name}".strip(),

                "first_name": user.first_name,

                "last_name": user.last_name,

                "profile_picture": profile_picture,

                "email_verified": email_verified,

                "raw_data": raw_data,

            },
        )

        if not created:

            changed = False

            if social.user != user:
                social.user = user
                changed = True

            if profile_picture and social.profile_picture != profile_picture:
                social.profile_picture = profile_picture
                changed = True

            if social.email_verified != email_verified:
                social.email_verified = email_verified
                changed = True

            if raw_data:
                social.raw_data = raw_data
                changed = True

            if changed:
                social.save()

        return social

    # ==========================================================
    # UPDATE USER
    # ==========================================================

    @staticmethod
    def update_user(
        user,
        first_name=None,
        last_name=None,
        email=None,
    ):

        changed = False

        if first_name is not None:

            user.first_name = first_name

            changed = True

        if last_name is not None:

            user.last_name = last_name

            changed = True

        if email is not None:

            user.email = email.lower()

            changed = True

        if changed:

            user.save()

        return user

    # ==========================================================
    # LOGIN
    # ==========================================================

    @staticmethod
    def login_user(request, user):

        login(request, user)

        return user

    # ==========================================================
    # LOGOUT
    # ==========================================================

    @staticmethod
    def logout_user(request):

        logout(request)

    # ==========================================================
    # DELETE SOCIAL ACCOUNT
    # ==========================================================

    @staticmethod
    def unlink_social_account(user, provider):

        SocialAccount.objects.filter(

            user=user,

            provider=provider,

        ).delete()