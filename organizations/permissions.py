# organizations/permissions.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from organizations.models.membership import OrganizationMember


def org_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):

        # 🔐 1. Must be logged in
        if not request.user.is_authenticated:
            
            from django.shortcuts import redirect
            return redirect("accounts:request-login-otp")


        # 🔐 2. Must have active organization
        active_org = getattr(request, "active_org", None)
        if not active_org:
            raise PermissionDenied("No active organization")

        # 🔐 3. Now it is SAFE to query DB
        member = OrganizationMember.objects.filter(
            user=request.user,
            organization=active_org,
            is_active=True,
        ).first()

        if not member or member.role != "org_admin":
            raise PermissionDenied("Org admin only")

        return view_func(request, *args, **kwargs)

    return _wrapped
