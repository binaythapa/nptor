from django.shortcuts import render, redirect, get_object_or_404
from organizations.permissions import org_admin_required
from quiz.models import Domain
from quiz.forms import DomainForm


@org_admin_required
def org_domain_list(request, slug):

    domains = Domain.objects.filter(is_active=True)

    return render(
        request,
        "organizations/admin/domains/list.html",
        {"domains": domains}
    )


@org_admin_required
def org_domain_create(request, slug):

    if request.method == "POST":

        form = DomainForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("organizations_admin:domain_list", slug=slug)

    else:
        form = DomainForm()

    return render(
        request,
        "organizations/admin/domains/create.html",
        {"form": form}
    )


@org_admin_required
def org_domain_edit(request, slug, pk):

    domain = get_object_or_404(Domain, pk=pk)

    if request.method == "POST":

        form = DomainForm(request.POST, instance=domain)

        if form.is_valid():
            form.save()
            return redirect(
                "organizations_admin:domain_list",
                slug=slug
            )

    else:
        form = DomainForm(instance=domain)

    return render(
        request,
        "organizations/admin/domains/edit.html",
        {
            "form": form,
            "domain": domain
        }
    )


@org_admin_required
def org_domain_delete(request, slug, pk):

    domain = get_object_or_404(Domain, pk=pk)

    domain.delete()

    return redirect(
        "organizations_admin:domain_list",
        slug=slug
    )