from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from organizations.models import OrganizationDomain
from organizations.permissions import org_admin_required
from organizations.services.domains import OrganizationDomainService


@org_admin_required
@require_http_methods(["GET", "POST"])
def organization_domains(request, slug):
    organization = request.organization
    if request.method == "POST":
        try:
            record = OrganizationDomainService.create(
                organization,
                request.POST.get("domain"),
                is_primary=request.POST.get("is_primary") == "on",
            )
            messages.success(request, f"Domain {record.domain} added. Verify it before activation.")
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        return redirect("organizations_admin:tenant_domains", slug=slug)
    return render(request, "organizations/admin/tenant_domains.html", {
        "org": organization,
        "domains": organization.domains.all(),
    })


@org_admin_required
@require_http_methods(["POST"])
def organization_domain_verify(request, slug, pk):
    record = get_object_or_404(OrganizationDomain, pk=pk, organization=request.organization)
    OrganizationDomainService.verify(record)
    messages.success(request, f"Domain {record.domain} verified.")
    return redirect("organizations_admin:tenant_domains", slug=slug)


@org_admin_required
@require_http_methods(["POST"])
def organization_domain_primary(request, slug, pk):
    record = get_object_or_404(OrganizationDomain, pk=pk, organization=request.organization)
    if not record.is_verified:
        messages.error(request, "Only verified domains can be primary.")
    else:
        OrganizationDomainService.set_primary(record)
        messages.success(request, f"Domain {record.domain} is now primary.")
    return redirect("organizations_admin:tenant_domains", slug=slug)
