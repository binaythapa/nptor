# organizations/middleware.py

from organizations.models.membership import OrganizationMember


class ActiveOrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("\n🔥🔥 MIDDLEWARE START 🔥🔥")

        request.active_org = None

        if request.user.is_authenticated:
            print("👤 USER:", request.user)

            memberships = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True
            )

            print("📦 MEMBERSHIPS:",
                list(memberships.values("organization_id", "role"))
            )

            admin_membership = memberships.filter(role="org_admin").first()
            print("⭐ ADMIN MEMBERSHIP:", admin_membership)

            if admin_membership:
                request.active_org = admin_membership.organization
            else:
                first = memberships.first()
                print("📌 FALLBACK MEMBERSHIP:", first)
                if first:
                    request.active_org = first.organization

        print("🏢 ACTIVE ORG FINAL:", request.active_org)
        print("🔥🔥 MIDDLEWARE END 🔥🔥\n")

        return self.get_response(request)
