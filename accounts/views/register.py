# accounts/views/register.py

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import EmailOTP
from accounts.models.profile import UserProfile

from accounts.services.cleanup import (
    delete_expired_unverified_users,
)

from accounts.services.otp_service import (
    create_registration_otp,
    verify_otp,
)

from accounts.utils.email import (
    send_registration_success_email,
)


# ============================================================
# USER MODEL
# ============================================================

User = get_user_model()


# ============================================================
# COUNTRY CHOICES
# ============================================================

COUNTRY_FIELD = UserProfile._meta.get_field("country")

COUNTRY_CHOICES = list(
    COUNTRY_FIELD.choices
)


# ============================================================
# REGISTER PAGE HELPER
# ============================================================

def render_register(
    request,
    *,
    error=None,
    first_name="",
    last_name="",
    email="",
    country="",
    phone="",
):
    """
    Render registration page while preserving submitted values.
    """

    return render(
        request,
        "accounts/auth/register.html",
        {
            "error": error,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "country": country,
            "phone": phone,
            "countries": COUNTRY_CHOICES,
        },
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_view(request):
    """
    Passwordless registration.

    Step 1:

        Registration form
              ↓
        Create/reuse inactive user
              ↓
        Create/reuse UserProfile
              ↓
        Generate registration OTP
              ↓
        Send OTP email
              ↓
        Store user ID in session
              ↓
        Redirect to OTP verification
    """

    # --------------------------------------------------------
    # CLEANUP OLD UNVERIFIED USERS
    # --------------------------------------------------------

    delete_expired_unverified_users(
        minutes=30
    )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    if request.method == "GET":

        return render_register(request)

    # --------------------------------------------------------
    # READ FORM DATA
    # --------------------------------------------------------

    first_name = (
        request.POST.get(
            "first_name",
            "",
        )
        .strip()
    )

    last_name = (
        request.POST.get(
            "last_name",
            "",
        )
        .strip()
    )

    email = (
        request.POST.get(
            "email",
            "",
        )
        .strip()
        .lower()
    )

    country = (
        request.POST.get(
            "country",
            "",
        )
        .strip()
        or None
    )

    phone = (
        request.POST.get(
            "phone",
            "",
        )
        .strip()
        or None
    )

    accepted_policy = request.POST.get(
        "accepted_policy"
    )

    # --------------------------------------------------------
    # REQUIRED FIELDS
    # --------------------------------------------------------

    if not first_name:

        return render_register(
            request,
            error="First name is required.",
            first_name=first_name,
            last_name=last_name,
            email=email,
            country=country or "",
            phone=phone or "",
        )

    if not last_name:

        return render_register(
            request,
            error="Last name is required.",
            first_name=first_name,
            last_name=last_name,
            email=email,
            country=country or "",
            phone=phone or "",
        )

    if not email:

        return render_register(
            request,
            error="Email address is required.",
            first_name=first_name,
            last_name=last_name,
            email=email,
            country=country or "",
            phone=phone or "",
        )

    # --------------------------------------------------------
    # EMAIL VALIDATION
    # --------------------------------------------------------

    try:

        validate_email(email)

    except ValidationError:

        return render_register(
            request,
            error="Enter a valid email address.",
            first_name=first_name,
            last_name=last_name,
            email=email,
            country=country or "",
            phone=phone or "",
        )

    # --------------------------------------------------------
    # TERMS & PRIVACY
    # --------------------------------------------------------

    if not accepted_policy:

        return render_register(
            request,
            error=(
                "You must accept the Terms & Privacy Policy."
            ),
            first_name=first_name,
            last_name=last_name,
            email=email,
            country=country or "",
            phone=phone or "",
        )

    # ========================================================
    # EXISTING USER
    # ========================================================

    existing_user = (
        User.objects
        .filter(
            email__iexact=email
        )
        .order_by("id")
        .first()
    )

    if existing_user:

        # ----------------------------------------------------
        # ACTIVE USER
        # ----------------------------------------------------

        if existing_user.is_active:

            return render_register(
                request,
                error=(
                    "An account with this email "
                    "already exists."
                ),
                first_name=first_name,
                last_name=last_name,
                email=email,
                country=country or "",
                phone=phone or "",
            )

        # ----------------------------------------------------
        # EXISTING INACTIVE USER
        # ----------------------------------------------------

        user = existing_user

        with transaction.atomic():

            user.first_name = first_name.title()
            user.last_name = last_name.title()

            # Passwordless account
            user.set_unusable_password()

            user.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "password",
                ]
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # A signal may already have created the profile.
            # Therefore NEVER use UserProfile.objects.create()
            # here.
            # ------------------------------------------------

            profile, _ = (
                UserProfile.objects.get_or_create(
                    user=user
                )
            )

            profile.country = country
            profile.phone = phone
            profile.phone_verified = False
            profile.accepted_policy = True
            profile.email_verified = False

            profile.save(
                update_fields=[
                    "country",
                    "phone",
                    "phone_verified",
                    "accepted_policy",
                    "email_verified",
                    "updated_at",
                ]
            )

        # ----------------------------------------------------
        # CREATE REGISTRATION OTP
        # ----------------------------------------------------

        create_registration_otp(
            user=user
        )

        request.session[
            "registration_user_id"
        ] = user.id

        return redirect(
            "accounts:verify-registration-otp"
        )

    # ========================================================
    # CREATE NEW USER
    # ========================================================

    with transaction.atomic():

        user = User.objects.create(
            username=email,
            first_name=first_name.title(),
            last_name=last_name.title(),
            email=email,
            is_active=False,
        )

        # ----------------------------------------------------
        # PASSWORDLESS ACCOUNT
        # ----------------------------------------------------

        user.set_unusable_password()

        user.save(
            update_fields=[
                "password",
            ]
        )

        # ----------------------------------------------------
        # CREATE OR REUSE USER PROFILE
        #
        # A post_save signal may already have created it.
        # get_or_create() prevents duplicate user_id errors.
        # ----------------------------------------------------

        profile, _ = (
            UserProfile.objects.get_or_create(
                user=user
            )
        )

        profile.country = country
        profile.phone = phone
        profile.phone_verified = False
        profile.email_verified = False
        profile.accepted_policy = True

        profile.save(
            update_fields=[
                "country",
                "phone",
                "phone_verified",
                "email_verified",
                "accepted_policy",
                "updated_at",
            ]
        )

    # ========================================================
    # CREATE REGISTRATION OTP
    # ========================================================

    create_registration_otp(
        user=user
    )

    # ========================================================
    # STORE USER IN SESSION
    # ========================================================

    request.session[
        "registration_user_id"
    ] = user.id

    # ========================================================
    # REDIRECT TO OTP VERIFICATION
    # ========================================================

    return redirect(
        "accounts:verify-registration-otp"
    )


# ============================================================
# EMAIL AVAILABILITY
# ============================================================

def check_email_availability(request):
    """
    AJAX endpoint for checking whether an active account
    already exists for the supplied email.
    """

    email = (
        request.GET.get(
            "email",
            "",
        )
        .strip()
        .lower()
    )

    if not email:

        return JsonResponse(
            {
                "available": False,
            }
        )

    exists = (
        User.objects
        .filter(
            email__iexact=email,
            is_active=True,
        )
        .exists()
    )

    return JsonResponse(
        {
            "available": not exists,
        }
    )


# ============================================================
# REGISTRATION OTP VERIFICATION
# ============================================================

def verify_registration_otp_view(request):
    """
    Step 2:

        Registration OTP
              ↓
        Verify OTP
              ↓
        Email verified
              ↓
        Account activated
              ↓
        Success page
    """

    # --------------------------------------------------------
    # GET USER ID FROM SESSION
    # --------------------------------------------------------

    user_id = request.session.get(
        "registration_user_id"
    )

    if not user_id:

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "Registration session expired.",
                "expires_in": 0,
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
            "registration_user_id",
            None,
        )

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "Invalid registration session.",
                "expires_in": 0,
            },
        )

    # --------------------------------------------------------
    # GET LATEST REGISTRATION OTP
    # --------------------------------------------------------

    otp_obj = (
        EmailOTP.objects
        .filter(
            user=user,
            purpose=EmailOTP.PURPOSE_REGISTRATION,
            is_used=False,
        )
        .order_by("-created_at")
        .first()
    )

    # --------------------------------------------------------
    # CALCULATE REMAINING TIME
    # --------------------------------------------------------

    expires_in = 0

    if otp_obj and otp_obj.expires_at:

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
    # --------------------------------------------------------

    if request.method == "GET":

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
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

    if not otp_code:

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "Please enter the OTP.",
                "expires_in": expires_in,
            },
        )

    # --------------------------------------------------------
    # OTP NOT FOUND
    # --------------------------------------------------------

    if not otp_obj:

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "OTP has expired.",
                "expires_in": 0,
            },
        )

    # --------------------------------------------------------
    # SERVER-SIDE EXPIRATION CHECK
    # --------------------------------------------------------

    if expires_in <= 0:

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "OTP has expired.",
                "expires_in": 0,
            },
        )

    # --------------------------------------------------------
    # VERIFY OTP
    # --------------------------------------------------------

    is_valid = verify_otp(
        user=user,
        code=otp_code,
        purpose=EmailOTP.PURPOSE_REGISTRATION,
    )

    if not is_valid:

        return render(
            request,
            "accounts/auth/verify_registration_otp.html",
            {
                "error": "Invalid or expired OTP.",
                "expires_in": expires_in,
            },
        )

    # ========================================================
    # ACTIVATE USER
    # ========================================================

    with transaction.atomic():

        user.is_active = True

        user.save(
            update_fields=[
                "is_active",
            ]
        )

        # ----------------------------------------------------
        # Get existing profile or create one.
        # ----------------------------------------------------

        profile, _ = (
            UserProfile.objects.get_or_create(
                user=user
            )
        )

        profile.email_verified = True

        profile.save(
            update_fields=[
                "email_verified",
                "updated_at",
            ]
        )

    # ========================================================
    # SEND REGISTRATION SUCCESS EMAIL
    # ========================================================

    send_registration_success_email(
        user=user
    )

    # ========================================================
    # CLEAR SESSION
    # ========================================================

    request.session.pop(
        "registration_user_id",
        None,
    )

    # ========================================================
    # REGISTRATION SUCCESS
    # ========================================================

    return redirect(
        "accounts:registration-success"
    )


# ============================================================
# REGISTRATION SUCCESS
# ============================================================

def registration_success_view(request):
    """
    Registration success page.
    """

    return render(
        request,
        "accounts/auth/registration_success.html",
    )