# organizations/permissions.py
from django.core.exceptions import PermissionDenied
from organizations.models.membership import OrganizationMember



def org_admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        print("\n🚪🚪 DECORATOR HIT 🚪🚪")
        print("👤 USER:", request.user)
        print("🏢 ACTIVE ORG:", getattr(request, "active_org", None))

        member = OrganizationMember.objects.filter(
            user=request.user,
            organization=getattr(request, "active_org", None),
            is_active=True,
        ).first()

        print("🎭 MEMBER:", member)
        if member:
            print("🎭 ROLE:", member.role)

        if not request.user.is_authenticated:
            raise PermissionDenied("Not authenticated")

        if not getattr(request, "active_org", None):
            raise PermissionDenied("No active organization")

        if not member or member.role != "org_admin":
            raise PermissionDenied("Org admin only")

        return view_func(request, *args, **kwargs)

    return _wrapped
