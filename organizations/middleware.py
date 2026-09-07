from organizations.models.membership import OrganizationMember
from organizations.services.tenant import TenantResolver


class ActiveOrganizationMiddleware:
    """Populate implicit user org plus explicit verified host tenant."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_org = None
        request.org_role = None
        request.organization = None
        request.tenant_source = None

        # A verified custom host is an authoritative tenant context.
        host_org = TenantResolver.by_host(request.get_host())
        if host_org:
            request.organization = host_org
            request.active_org = host_org
            request.tenant_source = "domain"

        if request.user.is_authenticated:
            memberships = (
                OrganizationMember.objects
                .filter(user=request.user, is_active=True)
                .select_related("organization")
            )
            admin_membership = memberships.filter(role="org_admin").first()
            membership = admin_membership or memberships.first()
            if membership:
                request.org_role = membership.role
                # Never override an explicit verified domain tenant.
                if request.organization is None:
                    request.active_org = membership.organization

        return self.get_response(request)
