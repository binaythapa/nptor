# organizations/permissions.py

from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from organizations.models.organization import Organization
from organizations.models.membership import OrganizationMember





def org_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, slug, *args, **kwargs):

        # 🔐 1. Must be logged in
        if not request.user.is_authenticated:
            return redirect("accounts:request-login-otp")

        # 🔐 2. Load organization from slug
        organization = get_object_or_404(Organization, slug=slug)

        # Attach to request (so views can use it)
        request.organization = organization
        request.active_org = organization  # optional consistency

        # 🔐 3. Verify membership
        member = OrganizationMember.objects.filter(
            user=request.user,
            organization=organization,
            is_active=True,
        ).first()

        if not member or member.role != "org_admin":
            raise PermissionDenied("Organization admin only.")

        return view_func(request, slug, *args, **kwargs)

    return _wrapped