from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from vendors.models import VendorProfile


def get_vendor_profile(user):
    """Return the VendorProfile associated with the user, or None."""
    if not user.is_authenticated:
        return None
    return getattr(user, "vendor_profile", None)


def is_approved_vendor(user):
    """Return True if user has an active, approved VendorProfile."""
    profile = get_vendor_profile(user)
    return profile is not None and profile.status == VendorProfile.STATUS_ACTIVE


def vendor_required(view_func):
    """
    Decorator for views that require an active approved vendor.
    - If unauthenticated: redirect to login.
    - If authenticated but no vendor profile: redirect to vendor onboarding.
    - If vendor profile is pending or suspended: redirect to vendor dashboard with notice.
    """
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        profile = get_vendor_profile(request.user)
        if profile is None:
            return redirect(reverse("vendors:onboarding"))
        if profile.status != VendorProfile.STATUS_ACTIVE:
            return redirect(reverse("vendors:dashboard"))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def vendor_or_staff_required(view_func):
    """Allows active vendors or staff/superusers."""
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_staff or is_approved_vendor(request.user):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Access restricted to active vendors and administrators.")
    return _wrapped_view
