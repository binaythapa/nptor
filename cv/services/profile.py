from accounts.models import UserProfile

from cv.models import CareerProfile


def get_or_create_career_profile(user):
    """Return the reusable career profile for an authenticated account."""
    profile, _ = CareerProfile.objects.get_or_create(user=user)
    return profile


def account_contact_defaults(user):
    """Return account-owned contact defaults for CV forms and rendering."""
    defaults = {
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "phone": "",
        "location": "",
    }

    try:
        account_profile = user.profile
    except (AttributeError, UserProfile.DoesNotExist):
        account_profile = None

    if account_profile is not None:
        defaults["phone"] = str(account_profile.phone or "")
        defaults["location"] = str(
            account_profile.address
            or account_profile.country
            or ""
        )

    return defaults
