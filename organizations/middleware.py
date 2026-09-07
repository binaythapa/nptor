from organizations.models.membership import OrganizationMember
from organizations.models.role import OrganizationRole
from organizations.services.tenant import TenantResolver


class ActiveOrganizationMiddleware:
    """Populate tenant context and route verified custom domains into org URLs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_org = None
        request.org_role = None
        request.organization = None
        request.organization_member = None
        request.tenant_source = None
        request.can_manage_organization = False

        raw_host = request.META.get("HTTP_HOST", "")
        host_org = TenantResolver.by_host(raw_host)
        if host_org:
            request.organization = host_org
            request.active_org = host_org
            request.tenant_source = "domain"

            # The custom host is authoritative. Prevent /org/<other-slug>/
            # paths from switching the tenant underneath that host.
            path = request.path_info or "/"
            if not path.startswith(f"/org/{host_org.slug}/"):
                request.path_info = f"/org/{host_org.slug}{path}"
                request.path = request.path_info

        if request.user.is_authenticated:
            memberships = (
                OrganizationMember.objects
                .filter(user=request.user, is_active=True)
                .select_related("organization")
            )
            if request.organization is not None:
                membership = memberships.filter(organization=request.organization).first()
            else:
                # Prefer an organization where the user has administration
                # capability when no tenant was explicitly resolved. This
                # makes the global dashboard's organization entry predictable
                # for users who belong to multiple organizations.
                admin_membership = memberships.filter(
                    role__in=OrganizationRole.administrative_roles()
                ).first()
                staff_membership = memberships.filter(
                    role=OrganizationRole.STAFF
                ).first()
                membership = admin_membership or staff_membership or memberships.first()

            if membership:
                request.org_role = membership.role
                request.organization_member = membership
                request.can_manage_organization = OrganizationRole.is_administrator(
                    membership.role
                )
                if request.organization is None:
                    request.active_org = membership.organization

        return self.get_response(request)
