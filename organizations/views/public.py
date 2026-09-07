from django.http import Http404
from django.shortcuts import get_object_or_404, render

from organizations.models.organization import Organization
from organizations.services.portal import OrganizationPortalService


def org_public_page(request, slug):
    """Published public portal for an active organization."""
    organization = get_object_or_404(Organization, slug=slug, is_active=True)
    context = OrganizationPortalService.published(organization)
    if not context["config"].is_published:
        raise Http404("Organization portal is not published.")
    return render(request, "organizations/public/organization.html", context)
