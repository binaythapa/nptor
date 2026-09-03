from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import Domain
from quiz.forms import DomainForm


@org_admin_required
def org_domain_list(request, slug):
    org = request.organization
    domains = Domain.objects.filter(
        organization=org,
        is_active=True,
    )
    return render(
        request,
        "organizations/admin/domains/list.html",
        {"domains": domains, "org": org},
    )


@org_admin_required
def org_domain_create(request, slug):
    org = request.organization
    if request.method == "POST":
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.organization = org
            domain.save()
            return redirect("organizations_admin:domain_list", slug=slug)
    else:
        form = DomainForm()
    return render(
        request,
        "organizations/admin/domains/create.html",
        {"form": form, "org": org},
    )


@org_admin_required
def org_domain_edit(request, slug, pk):
    org = request.organization
    domain = get_object_or_404(Domain, pk=pk, organization=org)
    if request.method == "POST":
        form = DomainForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            return redirect("organizations_admin:domain_list", slug=slug)
    else:
        form = DomainForm(instance=domain)
    return render(
        request,
        "organizations/admin/domains/edit.html",
        {"form": form, "domain": domain, "org": org},
    )


@require_POST
@org_admin_required
def org_domain_delete(request, slug, pk):
    org = request.organization
    domain = get_object_or_404(Domain, pk=pk, organization=org)
    domain.delete()
    return redirect("organizations_admin:domain_list", slug=slug)