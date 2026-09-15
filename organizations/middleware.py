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

            path = request.path_info or "/"
            if not path.startswith(f"/org/{host_org.slug}/"):
                request.path_info = f"/org/{host_org.slug}{path}"
                request.path = request.path_info
        else:
            # Resolve explicit /org/<slug>/ routes so views receive the same
            # organization context as custom-domain requests. This is
            # intentionally limited to active tenants.
            path = request.path_info or ""
            if path.startswith("/org/"):
                parts = path.split("/")
                if len(parts) > 2 and parts[2]:
                    path_org = TenantResolver.by_slug(parts[2])
                    if path_org:
                        request.organization = path_org
                        request.active_org = path_org
                        request.tenant_source = "path"

        if request.user.is_authenticated:
            memberships = (
                OrganizationMember.objects
                .filter(user=request.user, is_active=True)
                .select_related("organization")
            )
            if request.organization is not None:
                membership = memberships.filter(organization=request.organization).first()
            else:
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
