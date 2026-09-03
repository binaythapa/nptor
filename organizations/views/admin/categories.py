from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from organizations.permissions import org_admin_required
from quiz.models import Category, Domain
from quiz.forms import CategoryForm


def _org_domain_ids(org):
    return Domain.objects.filter(organization=org).values_list("id", flat=True)


@org_admin_required
def org_category_list(request, slug):
    org = request.organization
    categories = (
        Category.objects
        .filter(organization=org)
        .select_related("domain", "parent")
        .order_by("domain__name", "name")
    )
    return render(
        request,
        "organizations/admin/categories/list.html",
        {"categories": categories, "org": org},
    )


@org_admin_required
def org_category_create(request, slug):
    org = request.organization
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.organization = org
            if category.domain_id and category.domain_id not in set(_org_domain_ids(org)):
                messages.error(request, "Category domain must belong to this organization.")
            elif category.parent_id and category.parent and category.parent.organization_id != org.id:
                messages.error(request, "Category parent must belong to this organization.")
            else:
                category.save()
                return redirect("organizations_admin:category_list", slug=slug)
    else:
        form = CategoryForm()
    return render(
        request,
        "organizations/admin/categories/create.html",
        {"form": form, "org": org},
    )


@org_admin_required
def org_category_edit(request, slug, pk):
    org = request.organization
    category = get_object_or_404(Category, pk=pk, organization=org)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.domain_id and updated.domain.organization_id != org.id:
                messages.error(request, "Category domain must belong to this organization.")
            elif updated.parent_id and updated.parent.organization_id != org.id:
                messages.error(request, "Category parent must belong to this organization.")
            else:
                updated.organization = org
                updated.save()
                return redirect("organizations_admin:category_list", slug=slug)
    else:
        form = CategoryForm(instance=category)
    return render(
        request,
        "organizations/admin/categories/edit.html",
        {"form": form, "category": category, "org": org},
    )


@require_POST
@org_admin_required
def org_category_delete(request, slug, pk):
    org = request.organization
    category = get_object_or_404(Category, pk=pk, organization=org)
    category.delete()
    return redirect("organizations_admin:category_list", slug=slug)