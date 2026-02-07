from organizations.models.membership import OrganizationMember


class ActiveOrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("\n🔥🔥 MIDDLEWARE START 🔥🔥")

        request.active_org = None
        request.org_role = None   # 👈 ADD THIS

        if request.user.is_authenticated:
            print("👤 USER:", request.user)

            memberships = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True
            ).select_related("organization")

            print(
                "📦 MEMBERSHIPS:",
                list(memberships.values("organization_id", "role"))
            )

            # Prefer admin membership
            admin_membership = memberships.filter(role="org_admin").first()
            print("⭐ ADMIN MEMBERSHIP:", admin_membership)

            if admin_membership:
                request.active_org = admin_membership.organization
                request.org_role = admin_membership.role   # 👈 SET ROLE
            else:
                first = memberships.first()
                print("📌 FALLBACK MEMBERSHIP:", first)
                if first:
                    request.active_org = first.organization
                    request.org_role = first.role          # 👈 SET ROLE

        print("🏢 ACTIVE ORG FINAL:", request.active_org)
        print("🔑 ORG ROLE FINAL:", request.org_role)
        print("🔥🔥 MIDDLEWARE END 🔥🔥\n")

        return self.get_response(request)
